
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional

from modules.input_handler import NUMERIC_FIELDS
from modules.pdf_report import generate_pdf_report
from modules.simulator import find_max_safe_loan, simulate_cashflow
from modules.validator import ValidationError, validate_inputs

# --------------------------------------------------------------------------
# Brand palette (kept in sync with modules/pdf_report.py)
# --------------------------------------------------------------------------
NAVY = "#1B2A4A"
TEAL = "#0F9D8C"
SAFE_GREEN = "#2E7D32"
RISKY_AMBER = "#B8860B"
NOT_SAFE_RED = "#C62828"
LIGHT_GRAY = "#F2F4F7"
MID_GRAY = "#6B7280"
TEXT_DARK = "#1F2933"
INVALID_BG = "#FDEDED"
APP_BG = "#FFFFFF"

DECISION_COLORS = {"SAFE": SAFE_GREEN, "RISKY": RISKY_AMBER, "NOT SAFE": NOT_SAFE_RED}
RISK_COLORS = {"LOW": SAFE_GREEN, "MEDIUM": RISKY_AMBER, "HIGH": NOT_SAFE_RED}

LEFT_FIELDS = ["cash_balance", "monthly_revenue", "monthly_expenses", "existing_loan_payment"]
RIGHT_FIELDS = ["loan_amount", "interest_rate", "repayment_months"]

SCHEDULE_COLUMNS = [
    ("month", "Month", 60),
    ("revenue", "Revenue", 100),
    ("expenses", "Expenses", 100),
    ("existing_loan_payment", "Existing Debt", 100),
    ("emi", "EMI", 90),
    ("net_cashflow", "Net Cashflow", 100),
    ("ending_cash", "Ending Cash", 110),
]


def _money(value: float) -> str:
    return f"{value:,.2f}"


class CashflowPlannerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cashflow Loan Planner")
        self.geometry("1080x780")
        self.minsize(960, 680)
        self.configure(bg=APP_BG)

        self.entries: Dict[str, ttk.Entry] = {}
        self.results: Optional[dict] = None
        self.max_safe_loan: Optional[float] = None

        self._build_style()
        self._build_header()
        self._build_body()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=APP_BG)
        style.configure("Card.TLabelframe", background=APP_BG, borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background=APP_BG, foreground=NAVY,
                         font=("Helvetica", 11, "bold"))
        style.configure("TLabel", background=APP_BG, foreground=TEXT_DARK, font=("Helvetica", 10))
        style.configure("Hint.TLabel", background=APP_BG, foreground=MID_GRAY, font=("Helvetica", 8))
        style.configure("TEntry", padding=5, fieldbackground="white")
        style.configure("Invalid.TEntry", padding=5, fieldbackground=INVALID_BG)

        style.configure("Primary.TButton", font=("Helvetica", 10, "bold"), padding=8,
                         background=TEAL, foreground="white")
        style.map("Primary.TButton", background=[("active", "#0C8475"), ("disabled", "#A9D9D2")])

        style.configure("Secondary.TButton", font=("Helvetica", 10), padding=8,
                         background=NAVY, foreground="white")
        style.map("Secondary.TButton", background=[("active", "#142038"), ("disabled", "#9AA5B5")])

        style.configure("Ghost.TButton", font=("Helvetica", 10), padding=8,
                         background=LIGHT_GRAY, foreground=TEXT_DARK)
        style.map("Ghost.TButton", background=[("active", "#E2E5EA")])

        style.configure("Treeview", rowheight=24, font=("Helvetica", 10), fieldbackground="white")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background=NAVY,
                         foreground="white")
        style.map("Treeview.Heading", background=[("active", NAVY)])

        style.configure("TNotebook", background=APP_BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Helvetica", 10), padding=(14, 8))

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=NAVY, height=78)
        header.pack(side="top", fill="x")

        text_frame = tk.Frame(header, bg=NAVY)
        text_frame.pack(side="left", padx=24, pady=14, anchor="w")

        title = tk.Label(text_frame, text="Cashflow Loan Planner", bg=NAVY, fg="white",
                          font=("Helvetica", 18, "bold"))
        title.pack(anchor="w")
        subtitle = tk.Label(text_frame, text="Business loan safety analysis & PDF report generator",
                             bg=NAVY, fg="#C9D4E3", font=("Helvetica", 10))
        subtitle.pack(anchor="w")

    def _build_body(self) -> None:
        body = ttk.Frame(self)
        body.pack(side="top", fill="both", expand=True, padx=18, pady=14)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        self._build_input_panel(body, "Current Business Finances", LEFT_FIELDS, column=0)
        self._build_input_panel(body, "Proposed New Loan", RIGHT_FIELDS, column=1)

        action_row = ttk.Frame(body)
        action_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 10))

        self.generate_button = tk.Button(
            action_row, text="Generate Report", command=self.on_generate,
            bg=TEAL, fg="white", activebackground="#0C8475", activeforeground="white",
            font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=8,
            cursor="hand2", borderwidth=0,
        )
        self.generate_button.pack(side="left")

        self.export_button = tk.Button(
            action_row, text="Export to PDF", command=self.on_export,
            bg=MID_GRAY, fg="white", activebackground="#142038", activeforeground="white",
            disabledforeground="#E5E7EB",
            font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=8,
            cursor="hand2", borderwidth=0, state=tk.DISABLED,
        )
        self.export_button.pack(side="left", padx=10)

        self.reset_button = tk.Button(
            action_row, text="Reset", command=self.on_reset,
            bg=LIGHT_GRAY, fg=TEXT_DARK, activebackground="#E2E5EA",
            font=("Helvetica", 10), relief="flat", padx=16, pady=8,
            cursor="hand2", borderwidth=0,
        )
        self.reset_button.pack(side="left")

        results_frame = ttk.Frame(body)
        results_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        body.rowconfigure(2, weight=2)
        self._build_results_panel(results_frame)

    def _build_input_panel(self, parent, title, fields, column) -> None:
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=16)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column == 0 else (10, 0))
        frame.columnconfigure(1, weight=1)

        for row_idx, field in enumerate(fields):
            label_text, integer = NUMERIC_FIELDS[field]
            suffix = " (%)" if field == "interest_rate" else (" (months)" if field == "repayment_months" else "")
            display_label = label_text if suffix and suffix in label_text else label_text
            ttk.Label(frame, text=display_label + ":").grid(row=row_idx, column=0, sticky="w", pady=6, padx=(0, 10))
            entry = ttk.Entry(frame, width=22, justify="right")
            entry.grid(row=row_idx, column=1, sticky="ew", pady=6)
            entry.bind("<FocusIn>", lambda e, f=field: self._clear_invalid(f))
            self.entries[field] = entry

    def _build_results_panel(self, parent) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # --- Summary tab ---
        summary_tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(summary_tab, text="Summary")
        summary_tab.columnconfigure((0, 1, 2, 3), weight=1)

        self.decision_card = self._metric_card(summary_tab, "LOAN DECISION", "—", 0)
        self.risk_card = self._metric_card(summary_tab, "RISK LEVEL", "—", 1)
        self.emi_card = self._metric_card(summary_tab, "MONTHLY EMI", "—", 2, value_fg=NAVY, bg=LIGHT_GRAY)
        self.maxloan_card = self._metric_card(summary_tab, "MAX SAFE LOAN", "—", 3, value_fg=NAVY, bg=LIGHT_GRAY)

        self.liquidity_label = ttk.Label(summary_tab, text="Liquidity Status: —", font=("Helvetica", 10, "bold"))
        self.liquidity_label.grid(row=1, column=0, columnspan=4, pady=(14, 6), sticky="w")

        ttk.Label(summary_tab, text="Alerts", font=("Helvetica", 11, "bold")).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(10, 4))
        self.alerts_text = tk.Text(summary_tab, height=6, wrap="word", relief="solid", borderwidth=1,
                                    font=("Helvetica", 10), padx=10, pady=8)
        self.alerts_text.grid(row=3, column=0, columnspan=4, sticky="nsew")
        self.alerts_text.configure(state="disabled")
        summary_tab.rowconfigure(3, weight=1)

        # --- Monthly Schedule tab ---
        schedule_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(schedule_tab, text="Monthly Schedule")
        schedule_tab.columnconfigure(0, weight=1)
        schedule_tab.rowconfigure(0, weight=1)

        columns = [c[0] for c in SCHEDULE_COLUMNS]
        self.tree = ttk.Treeview(schedule_tab, columns=columns, show="headings")
        for col_id, heading, width in SCHEDULE_COLUMNS:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor="e" if col_id != "month" else "center")
        vsb = ttk.Scrollbar(schedule_tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("deficit", foreground=NOT_SAFE_RED)

        # --- Risk Analysis tab ---
        risk_tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(risk_tab, text="Risk Analysis")
        risk_tab.columnconfigure(0, weight=1)
        risk_tab.rowconfigure(1, weight=1)
        ttk.Label(risk_tab, text="Key Insights", font=("Helvetica", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.risk_text = tk.Text(risk_tab, wrap="word", relief="solid", borderwidth=1,
                                  font=("Helvetica", 10), padx=10, pady=8)
        self.risk_text.grid(row=1, column=0, sticky="nsew")
        self.risk_text.configure(state="disabled")

    def _metric_card(self, parent, label, value, column, value_fg="white", bg=NAVY):
        card = tk.Frame(parent, bg=bg, padx=10, pady=12, highlightthickness=1, highlightbackground=LIGHT_GRAY)
        card.grid(row=0, column=column, sticky="nsew", padx=6)
        label_fg = "white" if bg not in (LIGHT_GRAY, APP_BG) else MID_GRAY
        tk.Label(card, text=label, bg=bg, fg=label_fg, font=("Helvetica", 8, "bold")).pack()
        value_label = tk.Label(card, text=value, bg=bg, fg=value_fg, font=("Helvetica", 16, "bold"))
        value_label.pack(pady=(4, 0))
        card.value_label = value_label  # type: ignore[attr-defined]
        card.bg_default = bg  # type: ignore[attr-defined]
        return card

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg=LIGHT_GRAY, height=28)
        bar.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value="Ready. Fill in the figures above and click Generate Report.")
        ttk.Label(bar, textvariable=self.status_var, background=LIGHT_GRAY, foreground=MID_GRAY,
                  font=("Helvetica", 9)).pack(side="left", padx=12, pady=4)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _clear_invalid(self, field: str) -> None:
        self.entries[field].configure(style="TEntry")

    def _mark_invalid(self, field: str) -> None:
        self.entries[field].configure(style="Invalid.TEntry")

    def _reset_field_styles(self) -> None:
        for entry in self.entries.values():
            entry.configure(style="TEntry")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _set_export_enabled(self, enabled: bool) -> None:
        if enabled:
            self.export_button.configure(state=tk.NORMAL, bg=NAVY, cursor="hand2")
        else:
            self.export_button.configure(state=tk.DISABLED, bg=MID_GRAY, cursor="arrow")

    def on_generate(self) -> None:
        self._reset_field_styles()
        raw_data: Dict[str, float] = {}
        errors = []

        for field, (label, integer) in NUMERIC_FIELDS.items():
            raw_value = self.entries[field].get().strip()
            if raw_value == "":
                errors.append(f"{label} cannot be empty.")
                self._mark_invalid(field)
                continue
            try:
                value = int(raw_value) if integer else float(raw_value)
            except ValueError:
                expected = "a whole number" if integer else "a numeric value"
                errors.append(f"{label} must be {expected}.")
                self._mark_invalid(field)
                continue
            if value < 0:
                errors.append(f"{label} cannot be negative.")
                self._mark_invalid(field)
                continue
            raw_data[field] = value

        if errors:
            self._show_errors(errors)
            return

        try:
            validated_data = validate_inputs(raw_data)
            results = simulate_cashflow(validated_data)
            max_safe_loan = find_max_safe_loan(validated_data)
        except ValidationError as exc:
            self._show_errors(exc.errors)
            return
        except Exception as exc:  # unexpected runtime errors from the calc modules
            messagebox.showerror("Unexpected Error", f"Something went wrong while calculating:\n{exc}")
            return

        self.results = results
        self.max_safe_loan = max_safe_loan
        self._render_results(results, max_safe_loan)
        self._set_export_enabled(True)
        self.status_var.set("Report generated. Review the tabs below, then click Export to PDF.")

    def _show_errors(self, errors) -> None:
        message = "\n".join(f"\u2022 {e}" for e in errors)
        messagebox.showwarning("Please fix the following", message)
        self.status_var.set("Input validation failed — see highlighted fields.")

    def _render_results(self, results: dict, max_safe_loan: float) -> None:
        decision = results["decision"]
        risk_data = results["risk_data"]

        self._set_card(self.decision_card, decision, DECISION_COLORS.get(decision, NAVY))
        self._set_card(self.risk_card, risk_data["risk_level"], RISK_COLORS.get(risk_data["risk_level"], NAVY))
        self.emi_card.value_label.configure(text=_money(results["emi"]))
        self.maxloan_card.value_label.configure(text=_money(max_safe_loan))

        self.liquidity_label.configure(text=f"Liquidity Status: {risk_data['liquidity_status']}")

        alerts = list(results["inputs"].get("validation_warnings", []))
        alerts.extend(risk_data.get("alerts", []))
        if risk_data.get("over_leveraged"):
            alerts.append("Loan is over-leveraged relative to revenue/cashflow")
        if risk_data.get("low_buffer"):
            alerts.append("Cash buffer is below one month of expenses")
        if risk_data.get("unstable"):
            alerts.append("Cashflow is unstable in at least one month")
        deduped = []
        for a in alerts:
            if a not in deduped:
                deduped.append(a)

        self.alerts_text.configure(state="normal")
        self.alerts_text.delete("1.0", tk.END)
        if deduped:
            self.alerts_text.insert(tk.END, "\n".join(f"\u2022 {a}" for a in deduped))
        else:
            self.alerts_text.insert(tk.END, "No alerts — stable cashflow is projected for the full repayment term.")
        self.alerts_text.configure(state="disabled")

        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in results["schedule"]:
            tags = ("deficit",) if row["ending_cash"] < 0 else ()
            self.tree.insert("", tk.END, values=(
                row["month"], _money(row["revenue"]), _money(row["expenses"]),
                _money(row["existing_loan_payment"]), _money(row["emi"]),
                _money(row["net_cashflow"]), _money(row["ending_cash"]),
            ), tags=tags)

        reasons = risk_data.get("reasons") or ["No additional risk reasons found."]
        deficit_month = risk_data["cash_deficit_month"]
        self.risk_text.configure(state="normal")
        self.risk_text.delete("1.0", tk.END)
        self.risk_text.insert(tk.END, "\n".join(f"\u2022 {r}" for r in reasons))
        self.risk_text.insert(tk.END, f"\n\nFirst projected shortfall month: {deficit_month if deficit_month is not None else 'None'}")
        self.risk_text.insert(tk.END, f"\nLowest projected cash point: {_money(risk_data['min_cash_balance'])}")
        self.risk_text.configure(state="disabled")

    def _set_card(self, card, text, color_hex) -> None:
        card.configure(bg=color_hex)
        card.value_label.configure(bg=color_hex, fg="white")
        for child in card.winfo_children():
            if child is not card.value_label:
                child.configure(bg=color_hex, fg="white")
        card.value_label.configure(text=text)

    def on_export(self) -> None:
        if not self.results:
            messagebox.showinfo("No Report", "Generate a report first before exporting to PDF.")
            return

        default_name = f"Cashflow_Loan_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        path = filedialog.asksaveasfilename(
            title="Save PDF Report",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_name,
        )
        if not path:
            return

        try:
            generate_pdf_report(self.results, self.max_safe_loan, path)
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not generate the PDF report:\n{exc}")
            return

        self.status_var.set(f"PDF saved to: {path}")
        if messagebox.askyesno("Report Saved", f"Report saved to:\n{path}\n\nOpen it now?"):
            self._open_file(path)

    @staticmethod
    def _open_file(path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass  # opening is a convenience, not critical

    def on_reset(self) -> None:
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self._reset_field_styles()
        self.results = None
        self.max_safe_loan = None
        self._set_export_enabled(False)

        for card, label in ((self.decision_card, "LOAN DECISION"), (self.risk_card, "RISK LEVEL")):
            self._set_card(card, "—", NAVY)
        self.emi_card.value_label.configure(text="—")
        self.maxloan_card.value_label.configure(text="—")
        self.liquidity_label.configure(text="Liquidity Status: —")

        self.alerts_text.configure(state="normal")
        self.alerts_text.delete("1.0", tk.END)
        self.alerts_text.configure(state="disabled")

        for row in self.tree.get_children():
            self.tree.delete(row)

        self.risk_text.configure(state="normal")
        self.risk_text.delete("1.0", tk.END)
        self.risk_text.configure(state="disabled")

        self.status_var.set("Ready. Fill in the figures above and click Generate Report.")


def main() -> int:
    app = CashflowPlannerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
