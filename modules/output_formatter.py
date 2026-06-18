"""Human-readable report formatting for the Cashflow Loan Planner."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def _format_currency(value: float) -> str:
    return f"{value:,.2f}"


def _render_table(schedule: List[Dict[str, Any]]) -> str:
    headers = [
        "Month",
        "Revenue",
        "Expenses",
        "Existing Debt",
        "EMI",
        "Net Cashflow",
        "Ending Cash",
    ]

    rows: List[List[str]] = []
    for row in schedule:
        rows.append(
            [
                str(row["month"]),
                _format_currency(row["revenue"]),
                _format_currency(row["expenses"]),
                _format_currency(row["existing_loan_payment"]),
                _format_currency(row["emi"]),
                _format_currency(row["net_cashflow"]),
                _format_currency(row["ending_cash"]),
            ]
        )

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def line(parts: Iterable[str]) -> str:
        return " | ".join(part.ljust(widths[idx]) for idx, part in enumerate(parts))

    separator = "-+-".join("-" * width for width in widths)
    output = [line(headers), separator]
    output.extend(line(row) for row in rows)
    return "\n".join(output)


def generate_report(results: Dict[str, Any]) -> str:
    """Generate a full business-readable report."""
    inputs = results["inputs"]
    risk_data = results["risk_data"]
    schedule = results["schedule"]
    validation_warnings = inputs.get("validation_warnings", [])

    summary = [
        "SUMMARY",
        f"Decision          : {results['decision']}",
        f"Risk Level        : {risk_data['risk_level']}",
        f"Liquidity Status  : {risk_data['liquidity_status']}",
        f"Monthly EMI       : {_format_currency(results['emi'])}",
    ]

    alerts = list(validation_warnings)
    alerts.extend(risk_data.get("alerts", []))
    if risk_data.get("over_leveraged"):
        alerts.append("over-leveraged")
    if risk_data.get("low_buffer"):
        alerts.append("low cash buffer")
    if risk_data.get("unstable"):
        alerts.append("cashflow instability")

    deduped_alerts = []
    for alert in alerts:
        if alert not in deduped_alerts:
            deduped_alerts.append(alert)

    key_insights = [
        f"First failure month : {risk_data['cash_deficit_month'] if risk_data['cash_deficit_month'] is not None else 'None'}",
        f"Lowest cash point   : {_format_currency(risk_data['min_cash_balance'])}",
    ]

    reasons = risk_data.get("reasons", []) or ["No additional risk reasons found."]

    sections = [
        "\n".join(summary),
        "MONTHLY CASHFLOW TABLE\n" + _render_table(schedule),
        "ALERTS\n" + ("\n".join(f"- {item}" for item in deduped_alerts) if deduped_alerts else "- None"),
        "KEY INSIGHTS\n" + "\n".join(key_insights),
        "RISK REASONS\n" + "\n".join(f"- {reason}" for reason in reasons),
    ]
    return "\n\n".join(sections)
