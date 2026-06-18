"""Validation rules for the Cashflow Loan Planner."""

from __future__ import annotations

from numbers import Number
from typing import Any, Dict, List


class ValidationError(Exception):
    """Raised when required user inputs fail hard validation rules."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


REQUIRED_FIELDS = [
    "cash_balance",
    "monthly_revenue",
    "monthly_expenses",
    "existing_loan_payment",
    "loan_amount",
    "interest_rate",
    "repayment_months",
]


FLOAT_FIELDS = {
    "cash_balance",
    "monthly_revenue",
    "monthly_expenses",
    "existing_loan_payment",
    "loan_amount",
    "interest_rate",
}


def validate_inputs(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize inputs.

    Note: loan_amount=0 is treated as valid on purpose to satisfy the mandatory
    zero-loan test scenario in the specification.
    """
    if not isinstance(data, dict):
        raise ValidationError(["Input payload must be a dictionary."])

    errors: List[str] = []
    normalized: Dict[str, Any] = {}

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")
            continue

        value = data[field]
        if value in (None, ""):
            errors.append(f"{field} cannot be empty")
            continue

        if not isinstance(value, Number):
            errors.append(f"{field} must be numeric")
            continue

        if field == "repayment_months":
            if int(value) != value:
                errors.append("repayment_months must be a whole number")
                continue
            normalized[field] = int(value)
        elif field in FLOAT_FIELDS:
            normalized[field] = float(value)

    if errors:
        raise ValidationError(errors)

    if normalized["cash_balance"] < 0:
        errors.append("cash_balance must be greater than or equal to 0")
    if normalized["monthly_revenue"] < 0:
        errors.append("monthly_revenue must be greater than or equal to 0")
    if normalized["monthly_expenses"] < 0:
        errors.append("monthly_expenses must be greater than or equal to 0")
    if normalized["existing_loan_payment"] < 0:
        errors.append("existing_loan_payment must be greater than or equal to 0")
    if normalized["loan_amount"] < 0:
        errors.append("loan_amount must be greater than or equal to 0")
    if normalized["interest_rate"] < 0:
        errors.append("interest_rate must be greater than or equal to 0")
    if normalized["repayment_months"] <= 0:
        errors.append("repayment_months must be greater than 0")

    if errors:
        raise ValidationError(errors)

    warnings: List[str] = []
    if normalized["monthly_expenses"] > normalized["monthly_revenue"]:
        warnings.append("negative operating cashflow")
    if normalized["cash_balance"] < normalized["monthly_expenses"]:
        warnings.append("low liquidity risk")
    if normalized["monthly_revenue"] > 0 and normalized["existing_loan_payment"] > 0.40 * normalized["monthly_revenue"]:
        warnings.append("high debt burden")

    normalized["validation_warnings"] = warnings
    return normalized
