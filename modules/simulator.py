"""Simulation, risk analysis, decision engine, and max-loan search."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from modules.calculator import (
    build_cashflow_schedule,
    calculate_emi,
    calculate_dscr,
    calculate_dti,
    calculate_cash_reserve_ratio,
)
from modules.validator import validate_inputs


def risk_analyzer(schedule: List[Dict[str, float]], stability_adjustment: int = 0) -> Dict[str, Any]:
    """Analyze schedule risk and return structured risk data.
    
    Args:
        schedule: The monthly cashflow schedule.
        stability_adjustment: Points added/subtracted based on historical CSV data.
    """
    if not schedule:
        return {
            "risk_score": 0,
            "cash_deficit_month": None,
            "min_cash_balance": 0.0,
            "risk_level": "Critical Risk",
            "reasons": ["empty simulation schedule"],
            "alerts": ["CASHFLOW SIMULATION FAILED"],
            "metrics": {
                "dscr": 0.0,
                "dti": 100.0,
                "cash_reserve_months": 0.0
            }
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
    total_debt_payment = schedule[0]["total_debt_payment"]

    dscr = calculate_dscr(operating_cashflow, total_debt_payment)
    dti = calculate_dti(total_debt_payment, revenue)
    cash_reserve_min = calculate_cash_reserve_ratio(min_cash_balance, expenses)
    initial_reserve = calculate_cash_reserve_ratio(schedule[0]["opening_cash"], expenses)

    risk_score = 100
    reasons: List[str] = []
    alerts: List[str] = []

    # A. Cashflow Stability (30 points)
    if first_deficit_month is not None:
        risk_score -= 40
        alerts.append("CASH FAILURE")
        reasons.append(f"Cash balance falls below zero in month {first_deficit_month}.")
    else:
        unstable = any(row["net_cashflow"] <= 0 for row in schedule)
        if unstable:
            risk_score -= 20
            reasons.append("Monthly cashflow is unstable or non-positive in at least one month.")

    # B. Leverage Risk (30 points)
    if dti > 50:
        risk_score -= 30
        reasons.append(f"Debt-to-Income is critically high ({dti}%).")
    elif dti > 40:
        risk_score -= 15
        reasons.append(f"Debt-to-Income is moderately high ({dti}%).")

    # C. Liquidity Risk (20 points)
    if cash_reserve_min < 3:
        risk_score -= 20
        reasons.append("Cash reserve drops to dangerously low levels (< 3 months).")
    elif cash_reserve_min < 6:
        risk_score -= 10
        reasons.append("Cash reserve drops below 6 months.")

    # D. Debt Burden (20 points)
    if dscr < 1.2:
        risk_score -= 25
        reasons.append(f"DSCR is below acceptable threshold (< 1.2).")
    elif dscr < 1.5:
        risk_score -= 10
        reasons.append(f"DSCR is acceptable but leaves little room for error ({dscr}).")

    # E. Historical data stability adjustment
    if stability_adjustment > 0:
        reasons.append(f"Historical data: stable revenue history grants +{stability_adjustment} pts.")
    elif stability_adjustment < 0:
        reasons.append(f"Historical data: unstable revenue history applies {stability_adjustment} pts.")
    risk_score += stability_adjustment

    risk_score = max(0, min(100, risk_score))

    if risk_score >= 90:
        risk_level = "Very Safe"
    elif risk_score >= 75:
        risk_level = "Low Risk"
    elif risk_score >= 60:
        risk_level = "Moderate Risk"
    elif risk_score >= 40:
        risk_level = "High Risk"
    else:
        risk_level = "Critical Risk"

    if not reasons:
        reasons.append("Strong financial health across all metrics.")

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "cash_deficit_month": first_deficit_month,
        "min_cash_balance": round(min_cash_balance, 2),
        "reasons": reasons,
        "alerts": alerts,
        "metrics": {
            "dscr": dscr,
            "dti": dti,
            "cash_reserve_months": initial_reserve,
            "net_cashflow": schedule[0]["net_cashflow"]
        }
    }


def loan_decision_engine(risk_data: Dict[str, Any]) -> str:
    """Return SAFE / RISKY / NOT SAFE from risk analysis."""
    score = risk_data["risk_score"]
    if score >= 75:
        return "SAFE"
    if score >= 60:
        return "RISKY"
    return "NOT SAFE"


def simulate_cashflow(data: Dict[str, Any], stability_adjustment: int = 0) -> Dict[str, Any]:
    """Run the end-to-end simulation and assemble all output data."""
    validated_data = validate_inputs(data)
    emi = calculate_emi(
        validated_data["loan_amount"],
        validated_data["interest_rate"],
        validated_data["repayment_months"],
    )
    schedule = build_cashflow_schedule(validated_data, emi)
    risk_data = risk_analyzer(schedule, stability_adjustment=stability_adjustment)
    decision = loan_decision_engine(risk_data)

    return {
        "inputs": validated_data,
        "emi": round(emi, 2),
        "schedule": schedule,
        "risk_data": risk_data,
        "decision": decision,
    }


def run_scenarios(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run Base, Best, and Worst case scenarios and return comparative results."""
    scenarios = {
        "Base Case": {"revenue_multiplier": 1.0, "expense_multiplier": 1.0, "interest_delta": 0.0},
        "Best Case": {"revenue_multiplier": 1.15, "expense_multiplier": 0.95, "interest_delta": -1.0},
        "Worst Case": {"revenue_multiplier": 0.75, "expense_multiplier": 1.15, "interest_delta": 3.0},
    }
    
    results = {}
    for name, mods in scenarios.items():
        try:
            scenario_data = deepcopy(data)
            scenario_data["monthly_revenue"] *= mods["revenue_multiplier"]
            scenario_data["monthly_expenses"] *= mods["expense_multiplier"]
            scenario_data["interest_rate"] = max(0.0, scenario_data["interest_rate"] + mods["interest_delta"])
            
            sim = simulate_cashflow(scenario_data)
            
            results[name] = {
                "final_cash": sim["schedule"][-1]["ending_cash"] if sim["schedule"] else 0.0,
                "min_cash": sim["risk_data"]["min_cash_balance"],
                "cash_deficit_month": sim["risk_data"]["cash_deficit_month"],
                "avg_cashflow": sum(r["net_cashflow"] for r in sim["schedule"]) / max(1, len(sim["schedule"])),
                "risk_score": sim["risk_data"]["risk_score"]
            }
        except Exception:
            results[name] = None
            
    return results


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
