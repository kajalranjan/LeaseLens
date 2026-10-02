#!/usr/bin/env python3
"""Verify that every quote in a lease-check result appears word-for-word in the lease.

Usage:
    python verify_quotes.py LEASE.txt RESULT.json [--out VERIFIED.json]

Cards whose quote is not found in the lease are switched to found=false and
marked "verified": false, so an agent never shows a made-up clause.
Standard library only (Python 3.8+).
"""
import json
import re
import sys

_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
}


def normalize(text: str) -> str:
    """Lowercase, unify smart quotes/dashes, collapse whitespace."""
    for k, v in _REPLACEMENTS.items():
        text = text.replace(k, v)
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_in_text(quote: str, text: str) -> bool:
    q = normalize(quote).strip(" .\"'")
    return bool(q) and q in normalize(text)


def verify(lease_text: str, result: dict) -> dict:
    for card in result.get("clauses", []):
        if card.get("found") and card.get("quote"):
            ok = quote_in_text(card["quote"], lease_text)
            card["verified"] = ok
            if not ok:
                card["found"] = False
                card["quote"] = ""
        else:
            card["verified"] = False
    return result


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            lease = f.read()
        with open(argv[2], encoding="utf-8") as f:
            result = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    verified = verify(lease, result)
    out = json.dumps(verified, indent=2)
    if "--out" in argv:
        with open(argv[argv.index("--out") + 1], "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)
    dropped = sum(1 for c in verified["clauses"] if c.get("verified") is False and c.get("explanation"))
    print(f"verified: {sum(c.get('verified', False) for c in verified['clauses'])}, "
          f"not found/dropped: {dropped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
