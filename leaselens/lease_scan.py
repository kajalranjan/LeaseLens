"""Lease scan: open-weight model + word-for-word quote verification.

The prompt is built from the Agent Skill folder (skills/lease-check), so the app
and the published skill always share one clause checklist and one JSON format.

Contract:  scan_lease(text) -> list[card]
  card = {clause_type, label, found, quote, explanation, risk_level,
          question_to_ask, verified, start, end}
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from . import llm

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "lease-check"

CLAUSE_LABELS = {
    "security_deposit": "Security deposit",
    "early_termination": "Breaking the lease early",
    "auto_renewal": "Auto-renewal & notice",
    "utilities": "Utilities",
    "extra_fees": "Extra fees",
    "roommate_liability": "Roommate liability",
    "subletting": "Subletting",
    "maintenance": "Maintenance & repairs",
}

# Reuse the skill's verifier so there is exactly one implementation.
_spec = importlib.util.spec_from_file_location("verify_quotes", SKILL_DIR / "scripts" / "verify_quotes.py")
verify_quotes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_quotes)


def _system_prompt() -> str:
    clauses = (SKILL_DIR / "references" / "CLAUSES.md").read_text(encoding="utf-8")
    example = (SKILL_DIR / "assets" / "example_output.json").read_text(encoding="utf-8")
    return f"""You review apartment leases for first-time renters (age 18-22).
For EACH of these 8 clause types, find the passage in the lease that governs it:
{", ".join(CLAUSE_LABELS)}.

{clauses}

Return ONLY a JSON object: {{"clauses": [ ...exactly 8 objects, one per clause_type... ]}}
Each object has: clause_type, found (bool), quote, explanation, risk_level (low|medium|high), question_to_ask.

RULES:
- quote MUST be copied character-for-character from the lease. One contiguous passage. No "...", no paraphrase. Under 60 words.
- If the lease does not cover a clause type: found=false, quote="", and explain what is missing.
- explanation: 1-2 plain-English sentences about what it means for the renter's money or options.
- question_to_ask: one specific, polite question for the landlord.
- Do not say what the law requires.

Example of the format (partial):
{example}"""


def locate(quote: str, text: str) -> tuple[int, int] | None:
    """Find the quote's character span in the original text (whitespace/case tolerant)."""
    words = [re.escape(w) for w in verify_quotes.normalize(quote).strip(" .\"'").split(" ") if w]
    if not words:
        return None
    pattern = r"\s+".join(words)
    # tolerate smart quotes/dashes in the original
    pattern = pattern.replace("'", "['‘’]").replace('"', '["“”]').replace("\\-", "[-–—]")
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def _clean(cards: list, lease_text: str) -> list[dict]:
    seen, out = set(), []
    for c in cards:
        ct = str(c.get("clause_type", "")).strip().lower()
        if ct not in CLAUSE_LABELS or ct in seen:
            continue
        seen.add(ct)
        card = {
            "clause_type": ct, "label": CLAUSE_LABELS[ct],
            "found": bool(c.get("found")), "quote": str(c.get("quote") or "").strip(),
            "explanation": str(c.get("explanation") or "").strip(),
            "risk_level": str(c.get("risk_level") or "medium").lower(),
            "question_to_ask": str(c.get("question_to_ask") or "").strip(),
            "verified": False, "start": None, "end": None,
        }
        if card["risk_level"] not in ("low", "medium", "high"):
            card["risk_level"] = "medium"
        if card["found"] and card["quote"]:
            span = locate(card["quote"], lease_text)
            if span and verify_quotes.quote_in_text(card["quote"], lease_text):
                card["verified"] = True
                card["start"], card["end"] = span
                card["quote"] = lease_text[span[0]:span[1]]  # show the lease's exact wording
            else:
                # Model quoted something that isn't in the lease: drop the quote, keep it honest.
                card.update(found=False, quote="", dropped_hallucination=True)
        out.append(card)
    # Make sure all 8 types are present.
    for ct, label in CLAUSE_LABELS.items():
        if ct not in seen:
            out.append({"clause_type": ct, "label": label, "found": False, "quote": "",
                        "explanation": "The scan didn't return this clause type.",
                        "risk_level": "medium", "question_to_ask": "", "verified": False,
                        "start": None, "end": None})
    order = list(CLAUSE_LABELS)
    return sorted(out, key=lambda c: order.index(c["clause_type"]))


def scan_lease(text: str) -> list[dict]:
    """Ask the open model to fill one card per clause type, then verify every quote."""
    result = llm.chat_json(_system_prompt(), f"LEASE TEXT:\n<<<\n{text}\n>>>")
    cards = result.get("clauses", result if isinstance(result, list) else [])
    return _clean(cards, text)


def stats(cards: list[dict]) -> dict:
    return {
        "verified": sum(c["verified"] for c in cards),
        "dropped": sum(bool(c.get("dropped_hallucination")) for c in cards),
        "high": sum(c["found"] and c["risk_level"] == "high" for c in cards),
    }


def to_json(cards: list[dict]) -> str:
    keep = ("clause_type", "found", "quote", "explanation", "risk_level", "question_to_ask", "verified")
    return json.dumps({"clauses": [{k: c[k] for k in keep} for c in cards]}, indent=2)
