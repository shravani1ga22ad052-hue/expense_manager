from __future__ import annotations

import importlib.util
import tempfile
import unittest
from decimal import Decimal
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from expense_manager.src.expense_manager.processor import process_expenses
from expense_manager.src.expense_manager.reader import read_expense_file
from expense_manager.src.expense_manager.reporting import (
    build_summary_report,
    write_category_totals,
    write_cleaned_expenses,
    write_exception_log,
    write_report,
)


class ExpenseManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            [
                {
                    "employee_id": "E001",
                    "date": "2026-09-01",
                    "category": "Travel",
                    "amount": 1200.00,
                    "description": "Conference flight",
                    "approval_status": "approved",
                },
                {
                    "employee_id": "E001",
                    "date": "2026-09-03",
                    "category": "Meals",
                    "amount": 45.25,
                    "description": "Team lunch",
                    "approval_status": "approved",
                },
                {
                    "employee_id": "E002",
                    "date": "invalid-date",
                    "category": "Office",
                    "amount": 55.00,
                    "description": "Supplies",
                    "approval_status": "approved",
                },
                {
                    "employee_id": "E003",
                    "date": "2026-09-05",
                    "category": "Travel",
                    "amount": 80.00,
                    "description": "Taxi",
                    "approval_status": "rejected",
                },
            ]
        )

    def test_process_expenses_calculates_totals_and_flags_records(self) -> None:
        result = process_expenses(self.frame, large_threshold=Decimal("1000.00"))

        self.assertEqual(len(result.valid_records), 2)
        self.assertEqual(len(result.rejected_records), 2)
        self.assertEqual(len(result.large_expenses), 1)
        self.assertEqual(result.employee_totals["E001"], Decimal("1245.25"))
        self.assertEqual(result.category_totals["Travel"], Decimal("1200.00"))
        self.assertEqual(result.monthly_totals["2026-09"], Decimal("1245.25"))
        self.assertIn("E001", result.employee_category_totals)
        self.assertEqual(result.employee_category_totals["E001"]["Meals"], Decimal("45.25"))

    def test_report_generation_includes_key_sections(self) -> None:
        result = process_expenses(self.frame, large_threshold=Decimal("1000.00"))
        report = build_summary_report(result)

        self.assertIn("Monthly Expense Report", report)
        self.assertIn("Employee Totals", report)
        self.assertIn("Category Totals", report)
        self.assertIn("Large Expenses", report)
        self.assertIn("E001", report)

    def test_reader_supports_csv_and_excel(self) -> None:
        if importlib.util.find_spec("openpyxl") is None:
            self.skipTest("openpyxl is not available in this test environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "expenses.csv"
            xlsx_path = temp_path / "expenses.xlsx"
            self.frame.to_csv(csv_path, index=False)
            self.frame.to_excel(xlsx_path, index=False)

            csv_frame = read_expense_file(csv_path)
            xlsx_frame = read_expense_file(xlsx_path)

            self.assertEqual(len(csv_frame), 4)
            self.assertEqual(len(xlsx_frame), 4)
            self.assertIn("approval_status", csv_frame.columns)
            self.assertIn("approval_status", xlsx_frame.columns)

    def test_output_files_are_written(self) -> None:
        result = process_expenses(self.frame, large_threshold=Decimal("1000.00"))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cleaned_path = write_cleaned_expenses(result, temp_path / "cleaned.csv")
            category_totals_path = write_category_totals(result, temp_path / "category_totals.csv")
            exceptions_path = write_exception_log(result, temp_path / "exceptions.csv")
            report_path = write_report(result, temp_path / "report.txt")

            self.assertTrue(cleaned_path.exists())
            self.assertTrue(category_totals_path.exists())
            self.assertTrue(exceptions_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn("employee_id", cleaned_path.read_text(encoding="utf-8"))
            self.assertIn("category", category_totals_path.read_text(encoding="utf-8"))
            self.assertIn("reason", exceptions_path.read_text(encoding="utf-8"))
            self.assertIn("Monthly Expense Report", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
