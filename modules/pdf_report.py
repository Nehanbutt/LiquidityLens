

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")  # non-interactive backend, safe for use behind a GUI
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# Brand palette
# --------------------------------------------------------------------------
NAVY = colors.HexColor("#1B2A4A")
TEAL = colors.HexColor("#0F9D8C")
SAFE_GREEN = colors.HexColor("#2E7D32")
RISKY_AMBER = colors.HexColor("#B8860B")
NOT_SAFE_RED = colors.HexColor("#C62828")
LIGHT_GRAY = colors.HexColor("#F2F4F7")
ROW_STRIPE = colors.HexColor("#F7F8FA")
GRID_LINE = colors.HexColor("#E2E5EA")
MID_GRAY = colors.HexColor("#6B7280")
TEXT_DARK = colors.HexColor("#1F2933")

DECISION_COLORS = {
    "SAFE": SAFE_GREEN,
    "RISKY": RISKY_AMBER,
    "NOT SAFE": NOT_SAFE_RED,
}
RISK_LEVEL_COLORS = {
    "LOW": SAFE_GREEN,
    "MEDIUM": RISKY_AMBER,
    "HIGH": NOT_SAFE_RED,
}

FIELD_LABELS = {
    "cash_balance": "Current Cash Balance",
    "monthly_revenue": "Monthly Revenue",
    "monthly_expenses": "Monthly Expenses",
    "existing_loan_payment": "Existing Monthly Loan Payment",
    "loan_amount": "Requested New Loan Amount",
    "interest_rate": "Annual Interest Rate",
    "repayment_months": "Repayment Term",
}


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=22, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=10.5, textColor=MID_GRAY, alignment=TA_CENTER, spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, textColor=NAVY, spaceBefore=18, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=9.5, textColor=TEXT_DARK, leading=14,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontSize=9.5, textColor=TEXT_DARK,
            leading=14, leftIndent=14, bulletIndent=2, spaceAfter=4,
        ),
        "card_label": ParagraphStyle(
            "CardLabel", parent=base["Normal"], fontSize=8, textColor=MID_GRAY,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ),
        "card_label_white": ParagraphStyle(
            "CardLabelWhite", parent=base["Normal"], fontSize=8, textColor=colors.white,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ),
        "card_value": ParagraphStyle(
            "CardValue", parent=base["Normal"], fontSize=14, textColor=NAVY,
            alignment=TA_CENTER, fontName="Helvetica-Bold", spaceBefore=3,
        ),
        "card_value_white": ParagraphStyle(
            "CardValueWhite", parent=base["Normal"], fontSize=14, textColor=colors.white,
            alignment=TA_CENTER, fontName="Helvetica-Bold", spaceBefore=3,
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer", parent=base["Normal"], fontSize=8, textColor=MID_GRAY,
            leading=11, spaceBefore=10,
        ),
    }


def _build_chart_image(schedule: List[Dict[str, Any]]) -> str:
    """Render the cash-balance trend line chart to a temp PNG and return its path."""
    months = [row["month"] for row in schedule]
    ending_cash = [row["ending_cash"] for row in schedule]

    fig, ax = plt.subplots(figsize=(6.7, 2.7), dpi=200)
    ax.plot(months, ending_cash, color="#0F9D8C", linewidth=2.0, marker="o", markersize=2.5)
    ax.axhline(0, color="#C62828", linewidth=1, linestyle="--", alpha=0.8)
    ax.fill_between(
        months, ending_cash, 0,
        where=[v < 0 for v in ending_cash], color="#C62828", alpha=0.15, interpolate=True,
    )
    ax.fill_between(
        months, ending_cash, 0,
        where=[v >= 0 for v in ending_cash], color="#0F9D8C", alpha=0.10, interpolate=True,
    )
    ax.set_title("Projected Cash Balance Over Time", fontsize=11, color="#1B2A4A",
                  fontweight="bold", pad=10)
    ax.set_xlabel("Month", fontsize=9, color="#1F2933")
    ax.set_ylabel("Cash Balance", fontsize=9, color="#1F2933")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _pos: f"{x:,.0f}"))
    ax.tick_params(labelsize=8, colors="#1F2933")
    ax.grid(True, linestyle=":", linewidth=0.6, color="#D1D5DB")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()

    tmp_path = os.path.join(tempfile.gettempdir(), f"cashflow_chart_{os.getpid()}_{id(schedule)}.png")
    fig.savefig(tmp_path, transparent=True)
    plt.close(fig)
    return tmp_path


def _summary_cards(results: Dict[str, Any], max_safe_loan: float, styles: Dict[str, ParagraphStyle]) -> Table:
    decision = results["decision"]
    risk_data = results["risk_data"]
    decision_color = DECISION_COLORS.get(decision, NAVY)
    risk_color = RISK_LEVEL_COLORS.get(risk_data["risk_level"], NAVY)

    data = [
        [
            Paragraph("LOAN DECISION", styles["card_label_white"]),
            Paragraph("RISK LEVEL", styles["card_label_white"]),
            Paragraph("MONTHLY EMI", styles["card_label"]),
            Paragraph("MAX SAFE LOAN", styles["card_label"]),
        ],
        [
            Paragraph(decision, styles["card_value_white"]),
            Paragraph(risk_data["risk_level"], styles["card_value_white"]),
            Paragraph(_money(results["emi"]), styles["card_value"]),
            Paragraph(_money(max_safe_loan), styles["card_value"]),
        ],
    ]
    table = Table(data, colWidths=[1.725 * inch] * 4)
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, colors.white),
        ("BACKGROUND", (0, 0), (0, -1), decision_color),
        ("BACKGROUND", (1, 0), (1, -1), risk_color),
        ("BACKGROUND", (2, 0), (3, -1), LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _input_table(inputs: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    rows = [[Paragraph("Parameter", styles["card_label"]), Paragraph("Value", styles["card_label"])]]
    for field, label in FIELD_LABELS.items():
        value = inputs[field]
        if field == "interest_rate":
            display = f"{value:.2f}% per annum"
        elif field == "repayment_months":
            display = f"{int(value)} months"
        else:
            display = _money(value)
        rows.append([Paragraph(label, styles["body"]), Paragraph(display, styles["body"])])

    table = Table(rows, colWidths=[3.2 * inch, 3.7 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_STRIPE]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _schedule_table(schedule: List[Dict[str, Any]]) -> Table:
    header = ["Month", "Revenue", "Expenses", "Existing\nDebt", "EMI", "Net\nCashflow", "Ending\nCash"]
    data = [header]
    for row in schedule:
        data.append([
            str(row["month"]),
            _money(row["revenue"]),
            _money(row["expenses"]),
            _money(row["existing_loan_payment"]),
            _money(row["emi"]),
            _money(row["net_cashflow"]),
            _money(row["ending_cash"]),
        ])

    table = Table(
        data,
        colWidths=[0.5 * inch, 0.95 * inch, 0.95 * inch, 0.9 * inch, 0.75 * inch, 0.95 * inch, 0.95 * inch],
        repeatRows=1,
    )
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_STRIPE]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID_LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for idx, row in enumerate(schedule, start=1):
        if row["ending_cash"] < 0:
            style_cmds.append(("TEXTCOLOR", (6, idx), (6, idx), NOT_SAFE_RED))
            style_cmds.append(("FONTNAME", (6, idx), (6, idx), "Helvetica-Bold"))
    table.setStyle(TableStyle(style_cmds))
    return table


def _alerts_block(results: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    inputs = results["inputs"]
    risk_data = results["risk_data"]

    alerts: List[str] = list(inputs.get("validation_warnings", []))
    alerts.extend(risk_data.get("alerts", []))
    if risk_data.get("over_leveraged"):
        alerts.append("Loan is over-leveraged relative to revenue/cashflow")
    if risk_data.get("low_buffer"):
        alerts.append("Cash buffer is below one month of expenses")
    if risk_data.get("unstable"):
        alerts.append("Cashflow is unstable in at least one month")

    deduped: List[str] = []
    for alert in alerts:
        if alert not in deduped:
            deduped.append(alert)

    if not deduped:
        bg = colors.HexColor("#E8F5E9")
        border = SAFE_GREEN
        text = "No alerts — stable cashflow is projected for the full repayment term."
        para = Paragraph(text, ParagraphStyle("AlertOK", parent=styles["body"], textColor=SAFE_GREEN, fontName="Helvetica-Bold"))
    else:
        critical = risk_data["cash_deficit_month"] is not None
        bg = colors.HexColor("#FDECEA") if critical else colors.HexColor("#FFF6E5")
        border = NOT_SAFE_RED if critical else RISKY_AMBER
        text_color = NOT_SAFE_RED if critical else RISKY_AMBER
        items = "".join(f"&bull;&nbsp;&nbsp;{a}<br/>" for a in deduped)
        para = Paragraph(items, ParagraphStyle("AlertList", parent=styles["body"], textColor=text_color, fontName="Helvetica-Bold"))

    table = Table([[para]], colWidths=[6.9 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.2, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def _draw_footer(canvas_obj, doc) -> None:
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(GRID_LINE)
    canvas_obj.setLineWidth(0.75)
    canvas_obj.line(0.75 * inch, 0.65 * inch, letter[0] - 0.75 * inch, 0.65 * inch)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(MID_GRAY)
    canvas_obj.drawString(0.75 * inch, 0.48 * inch, "Cashflow Loan Planner \u2014 Generated Report")
    canvas_obj.drawRightString(letter[0] - 0.75 * inch, 0.48 * inch, f"Page {doc.page}")
    canvas_obj.restoreState()


def generate_pdf_report(results: Dict[str, Any], max_safe_loan: float, output_path: str) -> str:
    """Render simulation results into a polished PDF report and save to output_path.

    Parameters
    ----------
    results : dict
        The exact structure returned by ``modules.simulator.simulate_cashflow``.
    max_safe_loan : float
        The value returned by ``modules.simulator.find_max_safe_loan``.
    output_path : str
        Full path (including .pdf filename) to write the report to.

    Returns
    -------
    str
        The output_path, for convenience.
    """
    styles = _styles()
    chart_path = None

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.9 * inch,
        title="Cashflow Loan Planner Report",
        author="Cashflow Loan Planner",
    )

    story: List[Any] = []

    story.append(Paragraph("Cashflow Loan Planner", styles["title"]))
    story.append(Paragraph(
        f"Loan Safety &amp; Cashflow Report  &bull;  Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["subtitle"],
    ))
    rule = Table([[""]], colWidths=[6.9 * inch], rowHeights=[2.5])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TEAL)]))
    story.append(rule)
    story.append(Spacer(1, 16))

    story.append(_summary_cards(results, max_safe_loan, styles))
    story.append(Spacer(1, 4))
    liquidity_note = Paragraph(
        f"Liquidity Status: <b>{results['risk_data']['liquidity_status']}</b>",
        ParagraphStyle("LiquidityNote", parent=styles["body"], alignment=TA_CENTER, textColor=MID_GRAY, spaceBefore=4),
    )
    story.append(liquidity_note)

    story.append(Paragraph("Alerts", styles["section"]))
    story.append(_alerts_block(results, styles))

    story.append(Paragraph("Input Parameters", styles["section"]))
    story.append(_input_table(results["inputs"], styles))

    try:
        chart_path = _build_chart_image(results["schedule"])
        story.append(Paragraph("Cash Balance Trend", styles["section"]))
        story.append(Image(chart_path, width=6.7 * inch, height=2.7 * inch))
    except Exception:
        pass  # chart is a nice-to-have; never block the report on it

    story.append(Paragraph("Monthly Cashflow Schedule", styles["section"]))
    story.append(_schedule_table(results["schedule"]))

    reasons = results["risk_data"].get("reasons") or ["No additional risk reasons found."]
    story.append(Paragraph("Risk Analysis", styles["section"]))
    for reason in reasons:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{reason}", styles["bullet"]))

    deficit_month = results["risk_data"]["cash_deficit_month"]
    insight_text = (
        f"First projected shortfall month: <b>{deficit_month if deficit_month is not None else 'None'}</b>"
        f"&nbsp;&nbsp;|&nbsp;&nbsp;Lowest projected cash point: <b>{_money(results['risk_data']['min_cash_balance'])}</b>"
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph(insight_text, styles["body"]))

    story.append(Paragraph(
        "This report is generated automatically from the figures provided and is intended "
        "for internal planning purposes only. It does not constitute financial, legal, or "
        "investment advice.",
        styles["disclaimer"],
    ))

    try:
        doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    finally:
        if chart_path and os.path.exists(chart_path):
            try:
                os.remove(chart_path)
            except OSError:
                pass

    return output_path
