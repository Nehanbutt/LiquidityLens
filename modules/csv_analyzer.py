"""CSV import and historical analytics engine for the Cashflow Loan Planner.

Accepted CSV format (header row required):
    Month,Revenue,Expenses,Debt

'Debt' column is optional (defaults to 0 if missing).
"""

from __future__ import annotations

import csv
import statistics
from typing import Any, Dict, List, Optional, Tuple


class CSVParseError(Exception):
    """Raised when the CSV file cannot be parsed correctly."""
    pass


def load_csv(filepath: str) -> List[Dict[str, float]]:
    """
    Parse a CSV file into a list of monthly record dicts.

    Returns:
        List of dicts with keys: month_label, revenue, expenses, debt
    Raises:
        CSVParseError on bad format or missing required columns.
    """
    records: List[Dict[str, Any]] = []

    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise CSVParseError("CSV file appears to be empty.")

            # Normalize column names (strip whitespace, lowercase for matching)
            normalized = {col.strip().lower(): col for col in reader.fieldnames}

            if "revenue" not in normalized:
                raise CSVParseError("CSV must contain a 'Revenue' column.")
            if "expenses" not in normalized:
                raise CSVParseError("CSV must contain an 'Expenses' column.")

            rev_col = normalized["revenue"]
            exp_col = normalized["expenses"]
            debt_col = normalized.get("debt")
            month_col = normalized.get("month")

            for i, row in enumerate(reader, start=2):
                try:
                    revenue = float(str(row[rev_col]).replace(",", "").strip())
                    expenses = float(str(row[exp_col]).replace(",", "").strip())
                    debt = 0.0
                    if debt_col and row.get(debt_col, "").strip():
                        debt = float(str(row[debt_col]).replace(",", "").strip())
                    month_label = row[month_col].strip() if month_col else f"Month {i - 1}"
                    records.append({
                        "month_label": month_label,
                        "revenue": revenue,
                        "expenses": expenses,
                        "debt": debt,
                    })
                except (ValueError, KeyError) as exc:
                    raise CSVParseError(f"Invalid numeric value on row {i}: {exc}")

    except FileNotFoundError:
        raise CSVParseError(f"File not found: {filepath}")
    except UnicodeDecodeError:
        raise CSVParseError("Could not read the file. Please save it as UTF-8 CSV.")

    if len(records) < 2:
        raise CSVParseError("CSV must contain at least 2 data rows for trend analysis.")

    return records


def _linear_trend(values: List[float]) -> float:
    """Return the average monthly change using simple linear regression slope."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def analyze(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run historical analytics on the parsed CSV records.

    Returns a dict with:
        avg_revenue, avg_expenses, avg_debt,
        revenue_growth_pct, revenue_growth_label,
        volatility_level, volatility_score,
        stability_score, stability_adjustment,
        reasons
    """
    revenues = [r["revenue"] for r in records]
    expenses = [r["expenses"] for r in records]
    debts = [r["debt"] for r in records]

    avg_revenue = statistics.mean(revenues)
    avg_expenses = statistics.mean(expenses)
    avg_debt = statistics.mean(debts)

    # --- Revenue growth trend (linear regression slope as % of avg) ---
    slope = _linear_trend(revenues)
    revenue_growth_pct = (slope / avg_revenue * 100) if avg_revenue > 0 else 0.0
    if revenue_growth_pct > 1:
        revenue_growth_label = f"+{revenue_growth_pct:.1f}% per month (Growing)"
    elif revenue_growth_pct < -1:
        revenue_growth_label = f"{revenue_growth_pct:.1f}% per month (Declining)"
    else:
        revenue_growth_label = f"{revenue_growth_pct:.1f}% per month (Flat)"

    # --- Revenue volatility (coefficient of variation) ---
    rev_std = statistics.stdev(revenues) if len(revenues) > 1 else 0.0
    cv = (rev_std / avg_revenue * 100) if avg_revenue > 0 else 0.0
    if cv < 10:
        volatility_level = "LOW"
        volatility_score = 0       # No deduction
    elif cv < 25:
        volatility_level = "MEDIUM"
        volatility_score = -5
    else:
        volatility_level = "HIGH"
        volatility_score = -15

    # --- Expense control ratio ---
    avg_expense_ratio = avg_expenses / avg_revenue if avg_revenue > 0 else 1.0
    if avg_expense_ratio < 0.5:
        expense_score = 20
    elif avg_expense_ratio < 0.7:
        expense_score = 10
    elif avg_expense_ratio < 0.9:
        expense_score = 0
    else:
        expense_score = -15

    # --- Growth trend score ---
    if revenue_growth_pct > 3:
        growth_score = 20
    elif revenue_growth_pct > 0:
        growth_score = 10
    elif revenue_growth_pct > -3:
        growth_score = 0
    else:
        growth_score = -20

    # --- Stability Score (0–100) ---
    base = 60
    stability_score = max(0, min(100, base + growth_score + expense_score + volatility_score))

    # --- Risk adjustment to apply to main risk score ---
    if stability_score >= 75:
        stability_adjustment = +5
    elif stability_score >= 50:
        stability_adjustment = 0
    else:
        stability_adjustment = -10

    # --- Human-readable reasons ---
    reasons: List[str] = []
    reasons.append(f"Revenue trend: {revenue_growth_label}")
    reasons.append(f"Revenue volatility: {volatility_level} (CV={cv:.1f}%)")
    reasons.append(f"Average expense ratio: {avg_expense_ratio*100:.1f}% of revenue")
    if stability_adjustment > 0:
        reasons.append(f"Stable history grants +{stability_adjustment} pts to risk score.")
    elif stability_adjustment < 0:
        reasons.append(f"Unstable history applies {stability_adjustment} pts to risk score.")

    return {
        "records": records,
        "avg_revenue": round(avg_revenue, 2),
        "avg_expenses": round(avg_expenses, 2),
        "avg_debt": round(avg_debt, 2),
        "revenue_growth_pct": round(revenue_growth_pct, 2),
        "revenue_growth_label": revenue_growth_label,
        "volatility_level": volatility_level,
        "volatility_cv": round(cv, 2),
        "stability_score": stability_score,
        "stability_adjustment": stability_adjustment,
        "reasons": reasons,
    }
