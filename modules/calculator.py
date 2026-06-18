"""Calculation functions for EMI and month-wise schedule generation."""

from __future__ import annotations

from typing import Dict, List


ScheduleRow = Dict[str, float]


def calculate_emi(loan_amount: float, interest_rate: float, months: int) -> float:
    """Calculate EMI using the standard amortization formula."""
    if months <= 0:
        raise ValueError("months must be greater than 0")
    if loan_amount < 0:
        raise ValueError("loan_amount cannot be negative")
    if interest_rate < 0:
        raise ValueError("interest_rate cannot be negative")
    if loan_amount == 0:
        return 0.0

    monthly_rate = interest_rate / 12 / 100
    if monthly_rate == 0:
        return round(loan_amount / months, 2)

    growth_factor = (1 + monthly_rate) ** months
    emi = loan_amount * monthly_rate * growth_factor / (growth_factor - 1)
    return round(emi, 2)


def build_cashflow_schedule(data: Dict[str, float], emi: float) -> List[ScheduleRow]:
    """Build the monthly cashflow schedule and ending cash trajectory."""
    months = int(data["repayment_months"])
    cash_balance = float(data["cash_balance"])
    revenue = float(data["monthly_revenue"])
    expenses = float(data["monthly_expenses"])
    existing_loan_payment = float(data["existing_loan_payment"])
    operating_cashflow = revenue - expenses

    schedule: List[ScheduleRow] = []
    for month in range(1, months + 1):
        opening_cash = cash_balance
        total_debt_payment = existing_loan_payment + emi
        net_cashflow = revenue - expenses - total_debt_payment
        cash_balance = opening_cash + net_cashflow

        schedule.append(
            {
                "month": month,
                "opening_cash": round(opening_cash, 2),
                "revenue": round(revenue, 2),
                "expenses": round(expenses, 2),
                "existing_loan_payment": round(existing_loan_payment, 2),
                "emi": round(emi, 2),
                "total_debt_payment": round(total_debt_payment, 2),
                "operating_cashflow": round(operating_cashflow, 2),
                "net_cashflow": round(net_cashflow, 2),
                "ending_cash": round(cash_balance, 2),
            }
        )

    return schedule
