
from __future__ import annotations

import os
import subprocess
import sys

def _ensure_dependencies():
    required_packages = ["reportlab", "matplotlib"]
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Dependencies installed successfully.")
        except Exception as e:
            print(f"Failed to install dependencies: {e}")

_ensure_dependencies()

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional

from modules.input_handler import NUMERIC_FIELDS
from modules.pdf_report import generate_pdf_report
from modules.simulator import find_max_safe_loan, simulate_cashflow, run_scenarios
from modules.validator import ValidationError, validate_inputs
from modules.csv_analyzer import load_csv, analyze as analyze_csv, CSVParseError

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

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

LEFT_FIELDS = ["cash_balance", "monthly_revenue", "monthly_expenses"]
EXISTING_LOAN_FIELDS = ["existing_loan_payment"]
RIGHT_FIELDS = ["loan_amount", "interest_rate", "repayment_months"]

# Optional fields (not required, default to 0 if blank)
OPTIONAL_FIELDS = {
    "revenue_growth_rate": ("Revenue growth rate (% annual)", False),
    "expense_growth_rate": ("Expense growth rate (% annual)", False),
}
OPTIONAL_FIELD_NAMES = list(OPTIONAL_FIELDS.keys())

SCHEDULE_COLUMNS = [
    ("month", "Month", 60),
    ("revenue", "Revenue", 100),
    ("expenses", "Expenses", 100),
    ("existing_loan_payment", "Existing Pmt", 100),
    ("emi", "New EMI", 90),
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
        self.state("zoomed")
        self.configure(bg=APP_BG)

        self.entries: Dict[str, ttk.Entry] = {}
        self.results: Optional[dict] = None
        self.max_safe_loan: Optional[float] = None
        self.csv_analysis: Optional[dict] = None

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

        self._build_input_panel(body, "Current Business Finances", LEFT_FIELDS, column=0, existing_loan_fields=EXISTING_LOAN_FIELDS)
        self._build_input_panel(body, "Proposed New Loan", RIGHT_FIELDS, column=1, optional_fields=OPTIONAL_FIELD_NAMES)

        action_row = ttk.Frame(body)
        action_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 10))

        self.generate_button = tk.Button(
            action_row, text="Generate Report", command=self.on_generate,
            bg=TEAL, fg="white", activebackground="#0C8475", activeforeground="white",
            font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=8,
            cursor="hand2", borderwidth=0,
        )
        self.generate_button.pack(side="left")

        # Scenario buttons
        self.scenario_var = tk.StringVar(value="Base Case")
        for scen in ["Base Case", "Best Case", "Worst Case"]:
            rb = tk.Radiobutton(
                action_row, text=scen, variable=self.scenario_var, value=scen,
                bg=APP_BG, font=("Helvetica", 9), cursor="hand2"
            )
            rb.pack(side="left", padx=5)

        self.import_csv_button = tk.Button(
            action_row, text="📂 Import CSV", command=self.on_import_csv,
            bg="#4A5568", fg="white", activebackground="#2D3748", activeforeground="white",
            font=("Helvetica", 10, "bold"), relief="flat", padx=16, pady=8,
            cursor="hand2", borderwidth=0,
        )
        self.import_csv_button.pack(side="left", padx=(10, 0))

        self.csv_status_label = tk.Label(
            action_row, text="", bg=APP_BG, fg=TEAL,
            font=("Helvetica", 9, "italic")
        )
        self.csv_status_label.pack(side="left", padx=8)

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

    def _build_input_panel(self, parent, title, fields, column, optional_fields=None, existing_loan_fields=None) -> None:
        frame = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=16)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column == 0 else (10, 0))
        frame.columnconfigure(1, weight=1)

        next_row = 0
        for row_idx, field in enumerate(fields):
            label_text, integer = NUMERIC_FIELDS[field]
            suffix = " (%)" if field == "interest_rate" else (" (months)" if field == "repayment_months" else "")
            display_label = label_text if suffix and suffix in label_text else label_text
            ttk.Label(frame, text=display_label + ":").grid(row=row_idx, column=0, sticky="w", pady=6, padx=(0, 10))
            entry = ttk.Entry(frame, width=22, justify="right")
            entry.grid(row=row_idx, column=1, sticky="ew", pady=6)
            entry.bind("<FocusIn>", lambda e, f=field: self._clear_invalid(f))
            if field in ["loan_amount", "monthly_revenue"]:
                entry.bind("<FocusOut>", self._auto_fill_interest, add="+")
            entry.bind("<KeyRelease>", lambda e, f=field: self._format_commas(f))
            self.entries[field] = entry
            next_row += 1

        if existing_loan_fields:
            self.has_existing_loan_var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(frame, text="Has Existing Debt?", variable=self.has_existing_loan_var, command=self._toggle_existing_loan)
            cb.grid(row=next_row, column=0, columnspan=2, sticky="w", pady=(10, 4))
            next_row += 1

            self.existing_loan_widgets = []

            # Field 1: Monthly payment amount
            lbl1 = ttk.Label(frame, text="Monthly payment amount:")
            lbl1.grid(row=next_row, column=0, sticky="w", pady=4, padx=(0, 10))
            entry1 = ttk.Entry(frame, width=22, justify="right")
            entry1.grid(row=next_row, column=1, sticky="ew", pady=4)
            entry1.bind("<FocusIn>", lambda e: self._clear_invalid("existing_loan_payment"))
            entry1.bind("<KeyRelease>", lambda e: self._format_commas("existing_loan_payment"))
            hint1 = ttk.Label(frame, text="How much you pay each month on this debt", style="Hint.TLabel")
            hint1.grid(row=next_row + 1, column=0, columnspan=2, sticky="w", padx=(0, 10))
            self.entries["existing_loan_payment"] = entry1
            self.existing_loan_widgets.extend([(lbl1, entry1), (hint1, None)])
            next_row += 2

            # Field 2: Months remaining
            lbl2 = ttk.Label(frame, text="Months remaining on this debt:")
            lbl2.grid(row=next_row, column=0, sticky="w", pady=4, padx=(0, 10))
            entry2 = ttk.Entry(frame, width=22, justify="right")
            entry2.grid(row=next_row, column=1, sticky="ew", pady=4)
            entry2.bind("<FocusIn>", lambda e: self._clear_invalid("existing_loan_months"))
            entry2.bind("<KeyRelease>", lambda e: self._format_commas("existing_loan_months"))
            hint2 = ttk.Label(frame, text="Leave blank if debt is ongoing / no end date", style="Hint.TLabel")
            hint2.grid(row=next_row + 1, column=0, columnspan=2, sticky="w", padx=(0, 10))
            self.entries["existing_loan_months"] = entry2
            self.existing_loan_widgets.extend([(lbl2, entry2), (hint2, None)])
            next_row += 2

            self._toggle_existing_loan()

        if optional_fields:
            ttk.Label(frame, text="Optional Growth Rates", style="Hint.TLabel").grid(
                row=next_row, column=0, columnspan=2, sticky="w", pady=(10, 2))
            for i, field in enumerate(optional_fields):
                label_text, _ = OPTIONAL_FIELDS[field]
                ttk.Label(frame, text=label_text + ":").grid(
                    row=next_row + 1 + i, column=0, sticky="w", pady=4, padx=(0, 10))
                entry = ttk.Entry(frame, width=22, justify="right")
                entry.grid(row=next_row + 1 + i, column=1, sticky="ew", pady=4)
                entry.bind("<KeyRelease>", lambda e, f=field: self._format_commas(f))
                entry.insert(0, "0")  # default to 0
                self.entries[field] = entry

    def _format_commas(self, field: str) -> None:
        entry = self.entries[field]
        val = entry.get().replace(",", "")
        
        if not val or val == "-" or "." in val:
            return  # skip formatting if empty, just a minus, or has decimal
            
        try:
            # check if it's purely digits (with optional leading -)
            if (val.startswith("-") and val[1:].isdigit()) or val.isdigit():
                formatted = f"{int(val):,}"
                current_pos = entry.index(tk.INSERT)
                old_len = len(entry.get())
                entry.delete(0, tk.END)
                entry.insert(0, formatted)
                new_len = len(formatted)
                new_pos = current_pos + (new_len - old_len)
                entry.icursor(new_pos)
        except ValueError:
            pass

    def _toggle_existing_loan(self) -> None:
        show = self.has_existing_loan_var.get()
        for lbl, entry in self.existing_loan_widgets:
            if show:
                lbl.grid()
                if entry is not None:
                    entry.grid()
            else:
                lbl.grid_remove()
                if entry is not None:
                    entry.grid_remove()
                    entry.delete(0, tk.END)

    def _auto_fill_interest(self, event=None) -> None:
        try:
            loan_str = self.entries["loan_amount"].get().replace(",", "").strip()
            rev_str = self.entries["monthly_revenue"].get().replace(",", "").strip()
            int_str = self.entries["interest_rate"].get().replace(",", "").strip()
            
            if not int_str and loan_str and rev_str:
                loan = float(loan_str)
                rev = float(rev_str)
                if rev > 0:
                    estimated_rate = min(18.0, max(6.0, 8.0 + (loan / rev) * 0.5))
                    self.entries["interest_rate"].insert(0, str(round(estimated_rate, 2)))
        except ValueError:
            pass

    def _build_results_panel(self, parent) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # --- Summary tab ---
        summary_tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(summary_tab, text="Summary")
        summary_tab.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.decision_card = self._metric_card(summary_tab, "LOAN DECISION", "—", 0)
        self.score_card = self._metric_card(summary_tab, "RISK SCORE", "—", 1)
        self.dscr_card = self._metric_card(summary_tab, "DSCR", "—", 2, value_fg=NAVY, bg=LIGHT_GRAY)
        self.dti_card = self._metric_card(summary_tab, "DTI", "—", 3, value_fg=NAVY, bg=LIGHT_GRAY)
        self.maxloan_card = self._metric_card(summary_tab, "MAX SAFE LOAN", "—", 4, value_fg=NAVY, bg=LIGHT_GRAY)
        self.emi_card = self._metric_card(summary_tab, "EST. EMI", "—", 5, value_fg=NAVY, bg=LIGHT_GRAY)

        self.liquidity_label = ttk.Label(summary_tab, text="Cash Reserve: —", font=("Helvetica", 10, "bold"))
        self.liquidity_label.grid(row=1, column=0, columnspan=6, pady=(14, 6), sticky="w")

        ttk.Label(summary_tab, text="Reason:", font=("Helvetica", 11, "bold")).grid(
            row=2, column=0, columnspan=6, sticky="w", pady=(10, 4))
        self.alerts_text = tk.Text(summary_tab, height=10, wrap="word", relief="solid", borderwidth=1,
                                    font=("Helvetica", 10), padx=10, pady=8)
        self.alerts_text.grid(row=3, column=0, columnspan=6, sticky="nsew")
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
        
        # --- Charts tab ---
        charts_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(charts_tab, text="Charts")
        charts_tab.columnconfigure(0, weight=1)
        charts_tab.rowconfigure(0, weight=1)
        
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=charts_tab)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # --- Scenario Comparison tab ---
        scenarios_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(scenarios_tab, text="Scenario Comparison")
        scenarios_tab.columnconfigure(0, weight=1)
        scenarios_tab.rowconfigure(0, weight=1)
        
        columns = ("scenario", "final_cash", "min_cash", "avg_cashflow", "score")
        self.scenario_tree = ttk.Treeview(scenarios_tab, columns=columns, show="headings")
        self.scenario_tree.heading("scenario", text="Scenario")
        self.scenario_tree.heading("final_cash", text="Final Cash")
        self.scenario_tree.heading("min_cash", text="Min Cash")
        self.scenario_tree.heading("avg_cashflow", text="Avg Cashflow")
        self.scenario_tree.heading("score", text="Risk Score")
        self.scenario_tree.grid(row=0, column=0, sticky="nsew")

        # --- Historical Analysis tab ---
        hist_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(hist_tab, text="📊 Historical Analysis")
        hist_tab.columnconfigure(0, weight=1)
        hist_tab.rowconfigure(2, weight=1)

        # Top metric cards row
        hist_cards_frame = ttk.Frame(hist_tab)
        hist_cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for c in range(4):
            hist_cards_frame.columnconfigure(c, weight=1)

        self.hist_growth_card = self._metric_card(hist_cards_frame, "REVENUE TREND", "—", 0, value_fg=NAVY, bg=LIGHT_GRAY)
        self.hist_volatility_card = self._metric_card(hist_cards_frame, "VOLATILITY", "—", 1, value_fg=NAVY, bg=LIGHT_GRAY)
        self.hist_stability_card = self._metric_card(hist_cards_frame, "STABILITY SCORE", "—", 2, value_fg=NAVY, bg=LIGHT_GRAY)
        self.hist_adjustment_card = self._metric_card(hist_cards_frame, "RISK ADJUSTMENT", "—", 3, value_fg=NAVY, bg=LIGHT_GRAY)

        # Sparkline chart
        self.hist_figure = Figure(figsize=(8, 2.5), dpi=100)
        self.hist_canvas = FigureCanvasTkAgg(self.hist_figure, master=hist_tab)
        self.hist_canvas.get_tk_widget().grid(row=1, column=0, sticky="ew", pady=(0, 8))

        # Data table
        hist_cols = ("month", "revenue", "expenses", "debt")
        self.hist_tree = ttk.Treeview(hist_tab, columns=hist_cols, show="headings", height=6)
        self.hist_tree.heading("month", text="Month")
        self.hist_tree.heading("revenue", text="Revenue")
        self.hist_tree.heading("expenses", text="Expenses")
        self.hist_tree.heading("debt", text="Debt Payment")
        for col in hist_cols:
            self.hist_tree.column(col, anchor="center", width=120)
        hist_vsb = ttk.Scrollbar(hist_tab, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=hist_vsb.set)
        self.hist_tree.grid(row=2, column=0, sticky="nsew")
        hist_vsb.grid(row=2, column=1, sticky="ns")

        self.hist_no_data_label = ttk.Label(
            hist_tab, text="No CSV imported yet.\nUse '📂 Import CSV' to load your business history.",
            font=("Helvetica", 11), foreground=MID_GRAY, justify="center"
        )
        self.hist_no_data_label.grid(row=1, column=0, rowspan=2, pady=40)

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

        # Iterate over all defined numeric fields, omitting existing loan ones if checkbox is off
        fields_to_check = list(NUMERIC_FIELDS.keys())
        if hasattr(self, 'has_existing_loan_var') and not self.has_existing_loan_var.get():
            for f in EXISTING_LOAN_FIELDS:
                if f in fields_to_check:
                    fields_to_check.remove(f)

        for field in fields_to_check:
            if field not in self.entries:
                continue
            label, integer = NUMERIC_FIELDS[field]
            raw_value = self.entries[field].get().replace(",", "").strip()
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

        # Read optional growth rates (default to 0 if blank)
        for opt_field in OPTIONAL_FIELD_NAMES:
            val_str = self.entries[opt_field].get().replace(",", "").strip()
            raw_data[opt_field] = float(val_str) if val_str else 0.0

        # Read existing loan months remaining (optional — 0 means payment lasts forever)
        if hasattr(self, 'has_existing_loan_var') and self.has_existing_loan_var.get():
            elm_str = self.entries.get("existing_loan_months", None)
            elm_val = elm_str.get().replace(",", "").strip() if elm_str else ""
            raw_data["existing_loan_months"] = int(elm_val) if elm_val else 0

        try:
            validated_data = validate_inputs(raw_data)
            
            selected_scen = self.scenario_var.get()
            scenarios_mods = {
                "Base Case": {"revenue_multiplier": 1.0, "expense_multiplier": 1.0, "interest_delta": 0.0},
                "Best Case": {"revenue_multiplier": 1.15, "expense_multiplier": 0.95, "interest_delta": -1.0},
                "Worst Case": {"revenue_multiplier": 0.75, "expense_multiplier": 1.15, "interest_delta": 3.0},
            }
            mods = scenarios_mods[selected_scen]
            validated_data["monthly_revenue"] *= mods["revenue_multiplier"]
            validated_data["monthly_expenses"] *= mods["expense_multiplier"]
            validated_data["interest_rate"] = max(0.0, validated_data["interest_rate"] + mods["interest_delta"])

            results = simulate_cashflow(validated_data, stability_adjustment=self.csv_analysis["stability_adjustment"] if self.csv_analysis else 0)
            max_safe_loan = find_max_safe_loan(validated_data)
            scenario_results = run_scenarios(raw_data)
        except ValidationError as exc:
            self._show_errors(exc.errors)
            return
        except Exception as exc:  # unexpected runtime errors from the calc modules
            messagebox.showerror("Unexpected Error", f"Something went wrong while calculating:\n{exc}")
            return

        self.results = results
        self.max_safe_loan = max_safe_loan
        self._render_results(results, max_safe_loan, scenario_results)
        self._set_export_enabled(True)
        self.status_var.set("Report generated. Review the tabs below, then click Export to PDF.")

    def _show_errors(self, errors) -> None:
        message = "\n".join(f"\u2022 {e}" for e in errors)
        messagebox.showwarning("Please fix the following", message)
        self.status_var.set("Input validation failed — see highlighted fields.")

    def _render_results(self, results: dict, max_safe_loan: float, scenario_results: dict) -> None:
        decision = results["decision"]
        risk_data = results["risk_data"]
        metrics = risk_data.get("metrics", {})

        self._set_card(self.decision_card, decision, DECISION_COLORS.get(decision, NAVY))
        score = risk_data.get("risk_score", 0)
        score_color = SAFE_GREEN if score >= 75 else (RISKY_AMBER if score >= 60 else NOT_SAFE_RED)
        self._set_card(self.score_card, f"{score} / 100\n{risk_data.get('risk_level', 'UNKNOWN')}", score_color)
        
        dscr_val = "inf" if metrics.get('dscr') == float('inf') else str(metrics.get('dscr', '—'))
        self.dscr_card.value_label.configure(text=dscr_val)
        self.dti_card.value_label.configure(text=f"{metrics.get('dti', '—')}%")

        self.liquidity_label.configure(text=f"Cash Reserve: {metrics.get('cash_reserve_months', '—')} months")
        self.maxloan_card.value_label.configure(text=_money(max_safe_loan))
        self.emi_card.value_label.configure(text=_money(results["emi"]))

        self.alerts_text.configure(state="normal")
        self.alerts_text.delete("1.0", tk.END)
        for r in risk_data.get("reasons", []):
            self.alerts_text.insert(tk.END, f"\u2022 {r}\n")
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

        deficit_month = risk_data.get("cash_deficit_month")
        self.risk_text.configure(state="normal")
        self.risk_text.delete("1.0", tk.END)
        if scenario_results:
            worst_case = scenario_results.get("Worst Case")
            if worst_case and worst_case.get("cash_deficit_month"):
                self.risk_text.insert(tk.END, f"\u2022 Cash deficit begins in month {worst_case['cash_deficit_month']} under worst case scenario.\n")
            else:
                self.risk_text.insert(tk.END, f"\u2022 Business remains solvent under all tested scenarios.\n")
                
        self.risk_text.insert(tk.END, f"\nFirst projected shortfall month (Selected Case): {deficit_month if deficit_month is not None else 'None'}")
        self.risk_text.insert(tk.END, f"\nLowest projected cash point (Selected Case): {_money(risk_data['min_cash_balance'])}")
        self.risk_text.configure(state="disabled")

        # Draw charts
        self.figure.clear()
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        months = [r["month"] for r in results["schedule"]]
        cash = [r["ending_cash"] for r in results["schedule"]]
        rev = [r["revenue"] for r in results["schedule"]]
        exp = [r["expenses"] for r in results["schedule"]]
        
        ax1.plot(months, cash, color=TEAL, marker='o', markersize=4)
        ax1.set_title("Cash Balance Over Time")
        ax1.set_xlabel("Month")
        ax1.set_ylabel("Cash")
        
        ax2.plot(months, rev, color=SAFE_GREEN, label="Revenue")
        ax2.plot(months, exp, color=NOT_SAFE_RED, label="Expenses")
        ax2.set_title("Revenue vs Expenses")
        ax2.set_xlabel("Month")
        ax2.legend()
        
        self.figure.tight_layout()
        self.canvas.draw()

        # Populate Scenario Comparison
        for row in self.scenario_tree.get_children():
            self.scenario_tree.delete(row)
        for scen_name, scen_res in scenario_results.items():
            if scen_res:
                self.scenario_tree.insert("", tk.END, values=(
                    scen_name, _money(scen_res["final_cash"]), _money(scen_res["min_cash"]),
                    _money(scen_res["avg_cashflow"]), scen_res["risk_score"]
                ))

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

        # Reset existing debt checkbox and hide its fields
        if hasattr(self, 'has_existing_loan_var'):
            self.has_existing_loan_var.set(False)
            self._toggle_existing_loan()

        for card in (self.decision_card, self.score_card):
            self._set_card(card, "—", NAVY)
        self.dscr_card.value_label.configure(text="—")
        self.dti_card.value_label.configure(text="—")
        self.maxloan_card.value_label.configure(text="—")
        self.emi_card.value_label.configure(text="—")
        self.liquidity_label.configure(text="Cash Reserve: —")

        self.alerts_text.configure(state="normal")
        self.alerts_text.delete("1.0", tk.END)
        self.alerts_text.configure(state="disabled")

        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for row in self.scenario_tree.get_children():
            self.scenario_tree.delete(row)

        self.risk_text.configure(state="normal")
        self.risk_text.delete("1.0", tk.END)
        self.risk_text.configure(state="disabled")
        
        self.figure.clear()
        self.canvas.draw()

        self.status_var.set("Ready. Fill in the figures above and click Generate Report.")

    def on_import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Import Business History CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not path:
            return

        try:
            records = load_csv(path)
            self.csv_analysis = analyze_csv(records)
            
            # Fill inputs
            avg_rev = self.csv_analysis["avg_revenue"]
            avg_exp = self.csv_analysis["avg_expenses"]
            avg_debt = self.csv_analysis["avg_debt"]
            
            self.entries["monthly_revenue"].delete(0, tk.END)
            self.entries["monthly_revenue"].insert(0, str(int(avg_rev)))
            self._format_commas("monthly_revenue")

            self.entries["monthly_expenses"].delete(0, tk.END)
            self.entries["monthly_expenses"].insert(0, str(int(avg_exp)))
            self._format_commas("monthly_expenses")
            
            if avg_debt > 0:
                if not self.has_existing_loan_var.get():
                    self.has_existing_loan_var.set(True)
                    self._toggle_existing_loan()
                self.entries["existing_loan_payment"].delete(0, tk.END)
                self.entries["existing_loan_payment"].insert(0, str(int(avg_debt)))
                self._format_commas("existing_loan_payment")

            # Auto-fill revenue growth
            rev_growth = self.csv_analysis["revenue_growth_pct"]
            if "revenue_growth_rate" in self.entries:
                self.entries["revenue_growth_rate"].delete(0, tk.END)
                # Convert monthly trend approx to annual
                ann_growth = rev_growth * 12
                self.entries["revenue_growth_rate"].insert(0, str(round(ann_growth, 1)))

            # Update status
            self.csv_status_label.configure(text=f"Loaded {len(records)} months of data")
            
            # Update Historical Analysis Tab
            self.hist_no_data_label.grid_remove()
            
            self._set_card(self.hist_growth_card, self.csv_analysis["revenue_growth_label"], NAVY)
            
            vol_lvl = self.csv_analysis["volatility_level"]
            vol_color = SAFE_GREEN if vol_lvl == "LOW" else (RISKY_AMBER if vol_lvl == "MEDIUM" else NOT_SAFE_RED)
            self._set_card(self.hist_volatility_card, f"{vol_lvl}\n(CV: {self.csv_analysis['volatility_cv']}%)", vol_color)
            
            score = self.csv_analysis["stability_score"]
            score_color = SAFE_GREEN if score >= 75 else (RISKY_AMBER if score >= 50 else NOT_SAFE_RED)
            self._set_card(self.hist_stability_card, f"{score} / 100", score_color)
            
            adj = self.csv_analysis["stability_adjustment"]
            adj_str = f"+{adj}" if adj > 0 else str(adj)
            adj_color = SAFE_GREEN if adj > 0 else (NOT_SAFE_RED if adj < 0 else MID_GRAY)
            self._set_card(self.hist_adjustment_card, f"{adj_str} pts", adj_color)

            # Draw sparkline
            self.hist_figure.clear()
            ax = self.hist_figure.add_subplot(111)
            months = [r["month_label"] for r in records]
            revs = [r["revenue"] for r in records]
            exps = [r["expenses"] for r in records]
            
            ax.plot(months, revs, color=SAFE_GREEN, marker="o", label="Revenue")
            ax.plot(months, exps, color=NOT_SAFE_RED, marker="o", label="Expenses")
            ax.set_title("Historical Performance")
            ax.legend(loc="upper left")
            ax.grid(True, linestyle="--", alpha=0.6)
            self.hist_figure.tight_layout()
            self.hist_canvas.draw()
            
            # Fill tree
            for row in self.hist_tree.get_children():
                self.hist_tree.delete(row)
            for r in records:
                self.hist_tree.insert("", tk.END, values=(
                    r["month_label"], _money(r["revenue"]), _money(r["expenses"]), _money(r["debt"])
                ))
                
            self.notebook.select(2)  # switch to hist tab
            
        except CSVParseError as e:
            messagebox.showerror("CSV Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV:\n{e}")


def main() -> int:
    app = CashflowPlannerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
