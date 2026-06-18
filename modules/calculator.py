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
    """Build the monthly cashflow schedule and ending cash trajectory.

    Supports optional ``revenue_growth_rate`` and ``expense_growth_rate``
    fields (annual %, default 0).  The rates are converted to monthly
    compounding so that revenue and expenses change realistically over
    the loan term, producing curved charts instead of flat lines.
    """
    months = int(data["repayment_months"])
    cash_balance = float(data["cash_balance"])
    revenue = float(data["monthly_revenue"])
    expenses = float(data["monthly_expenses"])
    existing_loan_payment_base = float(data.get("existing_loan_payment", 0.0))
    existing_loan_months = int(data.get("existing_loan_months", 0))

    # Optional growth rates (annual %) → monthly multiplier
    rev_annual = float(data.get("revenue_growth_rate", 0.0))
    exp_annual = float(data.get("expense_growth_rate", 0.0))
    rev_monthly_mult = (1 + rev_annual / 100) ** (1 / 12)
    exp_monthly_mult = (1 + exp_annual / 100) ** (1 / 12)

    schedule: List[ScheduleRow] = []
    for month in range(1, months + 1):
        current_existing_payment = existing_loan_payment_base if (existing_loan_months == 0 or month <= existing_loan_months) else 0.0
        operating_cashflow = revenue - expenses
        opening_cash = cash_balance
        total_debt_payment = current_existing_payment + emi
        net_cashflow = revenue - expenses - total_debt_payment
        cash_balance = opening_cash + net_cashflow

        schedule.append(
            {
                "month": month,
                "opening_cash": round(opening_cash, 2),
                "revenue": round(revenue, 2),
                "expenses": round(expenses, 2),
                "existing_loan_payment": round(current_existing_payment, 2),
                "emi": round(emi, 2),
                "total_debt_payment": round(total_debt_payment, 2),
                "operating_cashflow": round(operating_cashflow, 2),
                "net_cashflow": round(net_cashflow, 2),
                "ending_cash": round(cash_balance, 2),
            }
        )

        # Apply monthly growth for next iteration
        revenue *= rev_monthly_mult
        expenses *= exp_monthly_mult

    return schedule


def calculate_dscr(operating_cashflow: float, total_debt_payment: float) -> float:
    """Calculate Debt Service Coverage Ratio."""
    if total_debt_payment <= 0:
        return float('inf')
    return round(operating_cashflow / total_debt_payment, 2)


def calculate_dti(total_debt_payment: float, revenue: float) -> float:
    """Calculate Debt-to-Income Ratio as a percentage."""
    if revenue <= 0:
        return 100.0 if total_debt_payment > 0 else 0.0
    return round((total_debt_payment / revenue) * 100, 2)


def calculate_cash_reserve_ratio(cash_balance: float, expenses: float) -> float:
    """Calculate Cash Reserve Ratio (months of survival)."""
    if expenses <= 0:
        return float('inf') if cash_balance > 0 else 0.0
    return round(cash_balance / expenses, 2)
