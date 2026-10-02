"""Budget math. Pure functions so they're easy to test and explain to judges."""
from __future__ import annotations

from dataclasses import dataclass, asdict

# Rough monthly utility estimates (electric + gas + water/sewer/trash + internet)
# for a whole unit, by bedroom count. Edit these to match your city.
UTILITY_ESTIMATE = {0: 140, 1: 160, 2: 210, 3: 260, 4: 310}
AFFORDABLE_SHARE = 0.30   # common "30% of income" guideline
STRETCH_SHARE = 0.40


@dataclass
class BudgetResult:
    rent_share: float
    utilities_share: float
    fees_share: float
    housing_total: float
    monthly_income: float
    other_expenses: float
    left_over: float
    housing_pct: float
    upfront_cost: float
    status: str          # "ok" | "stretch" | "over"

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_utilities(bedrooms: int) -> int:
    return UTILITY_ESTIMATE.get(bedrooms, UTILITY_ESTIMATE[4] + 50 * (bedrooms - 4))


def compute_budget(rent: float, bedrooms: int, monthly_income: float, roommates: int = 0,
                   utilities: float | None = None, monthly_fees: float = 0,
                   deposit: float | None = None, other_expenses: float = 0) -> BudgetResult:
    people = max(1, roommates + 1)
    utilities = estimate_utilities(bedrooms) if utilities is None else utilities
    deposit = rent if deposit is None else deposit

    rent_share = rent / people
    util_share = utilities / people
    fees_share = monthly_fees / people
    housing = rent_share + util_share + fees_share
    left = monthly_income - housing - other_expenses
    pct = housing / monthly_income if monthly_income > 0 else float("inf")

    if pct <= AFFORDABLE_SHARE:
        status = "ok"
    elif pct <= STRETCH_SHARE:
        status = "stretch"
    else:
        status = "over"

    return BudgetResult(
        rent_share=round(rent_share, 2), utilities_share=round(util_share, 2),
        fees_share=round(fees_share, 2), housing_total=round(housing, 2),
        monthly_income=round(monthly_income, 2), other_expenses=round(other_expenses, 2),
        left_over=round(left, 2), housing_pct=round(pct * 100, 1),
        upfront_cost=round(deposit / people + rent_share, 2),  # deposit share + first month
        status=status,
    )


def fallback_summary(b: BudgetResult) -> str:
    """Template summary used when the local model isn't running."""
    verdict = {"ok": "That's within the common 30% guideline.",
               "stretch": "That's above the 30% guideline, so money will be tight.",
               "over": "That's well above the 30% guideline; this place is likely too expensive for your income."}[b.status]
    return (f"Your share of rent, utilities and fees is about ${b.housing_total:,.0f}/month, "
            f"{b.housing_pct:.0f}% of your income. {verdict} After housing and other expenses "
            f"you'd have about ${b.left_over:,.0f}/month left. Plan on roughly ${b.upfront_cost:,.0f} "
            f"up front for your deposit share and first month.")
