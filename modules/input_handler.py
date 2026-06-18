"""Input collection helpers for the Cashflow Loan Planner."""

from typing import Dict


NUMERIC_FIELDS = {
    "cash_balance": ("Cash balance", False),
    "monthly_revenue": ("Monthly revenue", False),
    "monthly_expenses": ("Monthly expenses", False),
    "existing_loan_payment": ("Existing monthly loan payment", False),
    "loan_amount": ("New loan amount", False),
    "interest_rate": ("Annual interest rate (%)", False),
    "repayment_months": ("Repayment months", True),
}


def _read_numeric(prompt: str, integer: bool = False) -> float:
    while True:
        raw_value = input(f"{prompt}: ").strip()
        if raw_value == "":
            print("Value cannot be empty. Please try again.")
            continue

        try:
            value = int(raw_value) if integer else float(raw_value)
        except ValueError:
            expected = "an integer" if integer else "a numeric value"
            print(f"Invalid input. Please enter {expected}.")
            continue

        if value < 0:
            print("Negative values are not allowed here. Please try again.")
            continue

        return value


def get_user_inputs() -> Dict[str, float]:
    """Collect all required numeric inputs from the console safely."""
    data: Dict[str, float] = {}
    for field, (label, integer) in NUMERIC_FIELDS.items():
        data[field] = _read_numeric(label, integer=integer)
    return data
