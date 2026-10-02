import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from leaselens import budget, data, lease_scan  # noqa: E402

LEASE = (ROOT / "data" / "sample_lease.txt").read_text(encoding="utf-8")


def test_area_stats_mock_has_cheaper_nearby():
    s = data.get_area_stats("85281")
    assert s and s["source"] in ("mock", "snowflake-snapshot") and s["median_rent"] > 0
    assert s["nearby"] and s["nearby"][0]["median_rent"] < s["median_rent"]
    assert data.get_area_stats("99999") is None


def test_rent_vs_median():
    assert data.rent_vs_median(1600, 1677) == -4.6


def test_budget_split_and_status():
    r = budget.compute_budget(rent=1600, bedrooms=2, monthly_income=2000, roommates=1,
                              utilities=150, other_expenses=585)
    assert r.rent_share == 800 and r.housing_total == 875
    assert r.left_over == 540 and r.housing_pct == 43.8 and r.status == "over"


def test_real_quote_is_verified_and_located():
    q = "Each Tenant is jointly and severally liable for all obligations under this Lease"
    cards = lease_scan._clean([{"clause_type": "roommate_liability", "found": True, "quote": q,
                                "explanation": "x", "risk_level": "high", "question_to_ask": "y"}], LEASE)
    c = next(c for c in cards if c["clause_type"] == "roommate_liability")
    assert c["verified"] and LEASE[c["start"]:c["end"]] == q
    assert len(cards) == 8


def test_whitespace_and_smart_quotes_tolerated():
    q = "Tenants  shall not assign this Lease or\nsublet all or any part of the Premises."
    assert lease_scan.verify_quotes.quote_in_text(q, LEASE)
    assert lease_scan.locate(q, LEASE)


def test_hallucinated_quote_is_dropped():
    cards = lease_scan._clean([{"clause_type": "subletting", "found": True,
                                "quote": "Tenants may sublet with written approval.",
                                "explanation": "x", "risk_level": "low", "question_to_ask": "y"}], LEASE)
    c = next(c for c in cards if c["clause_type"] == "subletting")
    assert not c["verified"] and not c["found"] and c["quote"] == "" and c["dropped_hallucination"]


def test_skill_example_quote_appears_in_sample_lease():
    ex = json.loads((ROOT / "skills/lease-check/assets/example_output.json").read_text())
    for c in ex["clauses"]:
        if c["found"]:
            assert lease_scan.verify_quotes.quote_in_text(c["quote"], LEASE)


def test_skill_frontmatter_follows_spec():
    text = (ROOT / "skills/lease-check/SKILL.md").read_text()
    front = text.split("---")[1]
    fields = dict(line.split(":", 1) for line in front.strip().splitlines() if not line.startswith(" "))
    name = fields["name"].strip()
    assert name == "lease-check" == (ROOT / "skills/lease-check").name
    assert 0 < len(fields["description"].strip()) <= 1024
