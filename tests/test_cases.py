"""
Unit tests for the Cashflow Loan Planner.

Purpose of this file:
This file ensures that the core mathematical calculations and financial logic of the application
(such as simulate_cashflow, calculate_emi, and find_max_safe_loan) work correctly.

It automatically simulates different business scenarios:
- Healthy businesses (to ensure safe loans are approved)
- High debt pressure businesses (to ensure risky loans are flagged)
- Break-even businesses (to check edge cases)
- Input validation (feeding bad data like negative balances to ensure the app catches it)

Running these tests helps guarantee that future changes to the codebase do not accidentally
break the core financial logic.
"""

import unittest

from modules.calculator import calculate_emi
from modules.simulator import find_max_safe_loan, simulate_cashflow
from modules.validator import ValidationError, validate_inputs


class CashflowLoanPlannerTests(unittest.TestCase):
    def test_healthy_business(self):
        data = {
            "cash_balance": 50000,
            "monthly_revenue": 40000,
            "monthly_expenses": 20000,
            "existing_loan_payment": 2000,
            "loan_amount": 30000,
            "interest_rate": 10,
            "repayment_months": 12,
        }
        result = simulate_cashflow(data)
        self.assertEqual(result["decision"], "SAFE")
        self.assertTrue(all(row["ending_cash"] >= 0 for row in result["schedule"]))

    def test_high_debt_pressure(self):
        data = {
            "cash_balance": 5000,
            "monthly_revenue": 10000,
            "monthly_expenses": 7000,
            "existing_loan_payment": 1000,
            "loan_amount": 60000,
            "interest_rate": 18,
            "repayment_months": 12,
        }
        result = simulate_cashflow(data)
        self.assertIn(result["decision"], {"NOT SAFE", "RISKY"})
        self.assertIsNotNone(result["risk_data"]["cash_deficit_month"])

    def test_break_even_business(self):
        data = {
            "cash_balance": 10000,
            "monthly_revenue": 15000,
            "monthly_expenses": 14600,
            "existing_loan_payment": 0,
            "loan_amount": 2000,
            "interest_rate": 10,
            "repayment_months": 12,
        }
        result = simulate_cashflow(data)
        self.assertEqual(result["decision"], "RISKY")
        self.assertGreaterEqual(result["risk_data"]["min_cash_balance"], 0)

    def test_zero_loan_case(self):
        data = {
            "cash_balance": 8000,
            "monthly_revenue": 12000,
            "monthly_expenses": 9000,
            "existing_loan_payment": 0,
            "loan_amount": 0,
            "interest_rate": 10,
            "repayment_months": 12,
        }
        validated = validate_inputs(data)
        result = simulate_cashflow(validated)
        self.assertEqual(calculate_emi(0, 10, 12), 0.0)
        self.assertEqual(result["emi"], 0.0)
        self.assertIn(result["decision"], {"SAFE", "RISKY"})

    def test_edge_case_validation(self):
        with self.assertRaises(ValidationError):
            validate_inputs(
                {
                    "cash_balance": -1,
                    "monthly_revenue": 100,
                    "monthly_expenses": 50,
                    "existing_loan_payment": 0,
                    "loan_amount": 1000,
                    "interest_rate": 10,
                    "repayment_months": 12,
                }
            )

        with self.assertRaises(ValidationError):
            validate_inputs(
                {
                    "cash_balance": 1,
                    "monthly_revenue": 100,
                    "monthly_expenses": 50,
                    "existing_loan_payment": 0,
                    "loan_amount": 1000,
                    "interest_rate": 10,
                    "repayment_months": 0,
                }
            )

        with self.assertRaises(ValidationError):
            validate_inputs(
                {
                    "cash_balance": "",
                    "monthly_revenue": 100,
                    "monthly_expenses": 50,
                    "existing_loan_payment": 0,
                    "loan_amount": 1000,
                    "interest_rate": 10,
                    "repayment_months": 12,
                }
            )

    def test_find_max_safe_loan(self):
        data = {
            "cash_balance": 40000,
            "monthly_revenue": 30000,
            "monthly_expenses": 18000,
            "existing_loan_payment": 1000,
            "loan_amount": 10000,
            "interest_rate": 10,
            "repayment_months": 12,
        }
        max_safe = find_max_safe_loan(data)
        self.assertGreaterEqual(max_safe, 0)
        safe_result = simulate_cashflow({**data, "loan_amount": max_safe})
        self.assertEqual(safe_result["decision"], "SAFE")


if __name__ == "__main__":
    unittest.main()
