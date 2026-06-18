"""Simulation, risk analysis, decision engine, and max-loan search."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from modules.calculator import build_cashflow_schedule, calculate_emi
from modules.validator import validate_inputs


def risk_analyzer(schedule: List[Dict[str, float]]) -> Dict[str, Any]:
    """Analyze schedule risk and return structured risk data."""
    if not schedule:
        return {
            "cash_deficit_month": None,
            "min_cash_balance": 0.0,
            "liquidity_status": "NO DATA",
            "risk_level": "HIGH",
            "unstable": True,
            "over_leveraged": False,
            "low_buffer": True,
            "reasons": ["empty simulation schedule"],
            "alerts": ["CASHFLOW SIMULATION FAILED"],
        }

    ending_balances = [row["ending_cash"] for row in schedule]
    first_deficit_month: Optional[int] = next(
        (row["month"] for row in schedule if row["ending_cash"] < 0),
        None,
    )
    min_cash_balance = min(ending_balances)

    revenue = schedule[0]["revenue"]
    expenses = schedule[0]["expenses"]
    operating_cashflow = schedule[0]["operating_cashflow"]
    emi = schedule[0]["emi"]
    total_debt_payment = schedule[0]["total_debt_payment"]

    reasons: List[str] = []
    alerts: List[str] = []

    if first_deficit_month is not None:
        alerts.append("CASH FAILURE")
        reasons.append(f"Cash balance falls below zero in month {first_deficit_month}.")

    low_buffer = min_cash_balance < max(expenses, 1.0)
    if low_buffer:
        reasons.append("Cash buffer drops below one month of expenses.")

    unstable = any(row["net_cashflow"] <= 0 for row in schedule)
    if unstable:
        reasons.append("Monthly cashflow is unstable or non-positive in at least one month.")

    over_leveraged = False
    if revenue > 0:
        if total_debt_payment > 0.50 * revenue:
            over_leveraged = True
            reasons.append("Debt payments consume more than 50% of monthly revenue.")
        if emi > 0.60 * max(operating_cashflow, 1.0):
            over_leveraged = True
            reasons.append("New EMI dominates operating cashflow and creates leverage pressure.")
    elif total_debt_payment > 0:
        over_leveraged = True
        reasons.append("Debt payments exist while revenue is zero.")

    if first_deficit_month is not None:
        liquidity_status = "CRITICAL"
        risk_level = "HIGH"
    elif low_buffer or over_leveraged or unstable:
        liquidity_status = "LOW BUFFER"
        risk_level = "MEDIUM"
    else:
        liquidity_status = "ADEQUATE"
        risk_level = "LOW"

    if not reasons:
        reasons.append("Stable positive cashflow is maintained throughout the repayment term.")

    return {
        "cash_deficit_month": first_deficit_month,
        "min_cash_balance": round(min_cash_balance, 2),
        "liquidity_status": liquidity_status,
        "risk_level": risk_level,
        "unstable": unstable,
        "over_leveraged": over_leveraged,
        "low_buffer": low_buffer,
        "reasons": reasons,
        "alerts": alerts,
    }


def loan_decision_engine(risk_data: Dict[str, Any]) -> str:
    """Return SAFE / RISKY / NOT SAFE from risk analysis."""
    if risk_data["cash_deficit_month"] is not None:
        return "NOT SAFE"
    if risk_data["risk_level"] == "MEDIUM" or risk_data["low_buffer"] or risk_data["unstable"] or risk_data["over_leveraged"]:
        return "RISKY"
    return "SAFE"


def simulate_cashflow(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the end-to-end simulation and assemble all output data."""
    validated_data = validate_inputs(data)
    emi = calculate_emi(
        validated_data["loan_amount"],
        validated_data["interest_rate"],
        validated_data["repayment_months"],
    )
    schedule = build_cashflow_schedule(validated_data, emi)
    risk_data = risk_analyzer(schedule)
    decision = loan_decision_engine(risk_data)

    return {
        "inputs": validated_data,
        "emi": round(emi, 2),
        "schedule": schedule,
        "risk_data": risk_data,
        "decision": decision,
    }


def _decision_for_loan(data: Dict[str, Any], loan_amount: float) -> str:
    scenario = deepcopy(data)
    scenario["loan_amount"] = round(max(0.0, loan_amount), 2)
    result = simulate_cashflow(scenario)
    return result["decision"]


def find_max_safe_loan(data: Dict[str, Any]) -> float:
    """Find the maximum loan size that still returns SAFE using binary search."""
    validated_data = validate_inputs(data)

    if _decision_for_loan(validated_data, 0.0) == "NOT SAFE":
        return 0.0

    low = 0.0
    high = max(validated_data["loan_amount"], 1000.0)
    expansion_steps = 0
    while _decision_for_loan(validated_data, high) == "SAFE" and expansion_steps < 25:
        low = high
        high *= 2
        expansion_steps += 1

    for _ in range(60):
        mid = (low + high) / 2
        if _decision_for_loan(validated_data, mid) == "SAFE":
            low = mid
        else:
            high = mid

    return round(low, 2)
