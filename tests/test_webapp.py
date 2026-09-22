from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from expense_manager.src.expense_manager.webapp import app


class WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def test_index_page_renders_dashboard(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Expense Manager Showcase", body)
        self.assertIn("Built-in demo dataset", body)
        self.assertIn("Category Totals", body)
        self.assertIn("Add Expense Manually", body)
        self.assertIn("Clean sample dataset", body)

    def test_manual_expense_submission_updates_dashboard(self) -> None:
        response = self.client.post(
            "/",
            data={
                "action": "manual_add",
                "manual_employee_id": "E900",
                "manual_date": "2026-09-20",
                "manual_category": "Training",
                "manual_amount": "250.00",
                "manual_description": "Presentation practice",
                "manual_approval_status": "approved",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Manual expense added to the dashboard.", body)
        self.assertIn("E900", body)
        self.assertIn("Presentation practice", body)


if __name__ == "__main__":
    unittest.main()
