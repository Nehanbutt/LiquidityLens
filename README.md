# Cashflow Loan Planner — Desktop GUI

A native desktop application that analyses whether a business can safely take
on a new loan, and generates a polished multi-page PDF report with charts,
colour-coded risk indicators, and a full monthly cashflow schedule.

---

## What's New (GUI edition)

| Before | Now |
|--------|-----|
| All input typed in the terminal | Clean desktop window with labelled fields |
| Plain-text report printed to screen | Professional PDF saved wherever you choose |
| No visual feedback | Colour-coded SAFE / RISKY / NOT SAFE summary cards |
| Single run = single result | Three-tab view: Summary · Monthly Schedule · Risk Analysis |

The existing calculation engine (`modules/calculator.py`, `modules/simulator.py`,
`modules/validator.py`) is **unchanged** — only the input/output layer is new.

---

## Project Structure

```
cashflow_loan_planner/
├── gui_app.py                  ← Desktop GUI (run this)
├── main.py                     ← Original CLI entry-point (still works)
├── modules/
│   ├── calculator.py
│   ├── input_handler.py
│   ├── output_formatter.py
│   ├── pdf_report.py           ← NEW — professional PDF generator
│   ├── simulator.py
│   └── validator.py
└── tests/
    └── test_cases.py
```

---

## Requirements

- **Python 3.9 or later**
- **tkinter** — usually pre-installed with Python
  - macOS: comes with the official python.org installer
  - Windows: comes with the official python.org installer
  - Ubuntu/Debian Linux: `sudo apt install python3-tk`

> **⚡ Zero Setup Required:** You do **NOT** need to create virtual environments (`venv`) or run any `pip install` commands. The app will automatically fetch any required third-party dependencies the first time you run it!

---

## Setup & Running

```bash
# 1. Clone / unzip the project, then enter the folder
cd cashflow_loan_planner

# 2. Run the application directly!
python gui_app.py
```

The window opens immediately upon running. No internet connection required.

### Using the app

1. **Fill in the fields** — Current Business Finances on the left, Proposed New Loan on the right.
2. Click **Generate Report** — the three tabs below populate instantly.
3. Review the **Summary** (decision cards + alerts), **Monthly Schedule** (scrollable table), and **Risk Analysis** tabs.
4. Click **Export to PDF** — choose where to save the file. The app will offer to open it immediately.
5. Click **Reset** at any time to clear everything and start over.

---

## Running the original CLI (still works)

```bash
python main.py
```

---

## Packaging into a standalone .exe / .app (optional)

If you want to share the app with someone who doesn't have Python installed,
use **PyInstaller**:

```bash
pip install pyinstaller

# Windows — produces a single .exe
pyinstaller --onefile --windowed --name "CashflowLoanPlanner" gui_app.py

# macOS — produces a .app bundle
pyinstaller --onefile --windowed --name "CashflowLoanPlanner" gui_app.py

# Linux — produces a single binary
pyinstaller --onefile --name "CashflowLoanPlanner" gui_app.py
```

The output ends up in the `dist/` folder.

> **Note:** The first `--onefile` build can take 60–90 seconds and the
> resulting file will be 30–60 MB (it bundles Python + all libraries).
> That is normal.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'tkinter'` | `sudo apt install python3-tk` (Linux) or re-install Python from python.org (Windows/macOS) |
| Window opens but is tiny / cut off | Drag the corner to resize — the layout is fully responsive |
| PDF export fails silently | Check you have write permission to the chosen folder |
