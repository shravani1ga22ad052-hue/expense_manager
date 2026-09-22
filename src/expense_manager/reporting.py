from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from .models import ExpenseProcessingResult


def format_currency(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def build_summary_report(result: ExpenseProcessingResult) -> str:
    lines: list[str] = []
    lines.append("Monthly Expense Report")
    lines.append("======================")
    lines.append(f"Valid expenses: {len(result.valid_records)}")
    lines.append(f"Rejected expenses: {len(result.rejected_records)}")
    lines.append(f"Flagged large expenses: {len(result.large_expenses)}")
    lines.append("")

    lines.append("Employee Totals")
    lines.append("---------------")
    if result.employee_totals:
        for employee_id, amount in sorted(result.employee_totals.items()):
            lines.append(f"{employee_id}: {format_currency(amount)}")
    else:
        lines.append("No valid employee totals available.")
    lines.append("")

    lines.append("Category Totals")
    lines.append("---------------")
    if result.category_totals:
        for category, amount in sorted(result.category_totals.items()):
            lines.append(f"{category}: {format_currency(amount)}")
    else:
        lines.append("No valid category totals available.")
    lines.append("")

    lines.append("Monthly Totals")
    lines.append("--------------")
    if result.monthly_totals:
        for month, amount in sorted(result.monthly_totals.items()):
            lines.append(f"{month}: {format_currency(amount)}")
    else:
        lines.append("No valid monthly totals available.")
    lines.append("")

    lines.append("Large Expenses")
    lines.append("--------------")
    if result.large_expenses:
        for record in result.large_expenses:
            lines.append(
                f"Row {record.source_row} | {record.employee_id} | {record.date.isoformat()} | "
                f"{record.category} | {format_currency(record.amount)} | {record.description}"
            )
    else:
        lines.append("No large expenses exceeded the threshold.")

    return "\n".join(lines) + "\n"


def write_cleaned_expenses(result: ExpenseProcessingResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "employee_id",
                "date",
                "category",
                "amount",
                "description",
                "approval_status",
                "source_row",
            ],
        )
        writer.writeheader()
        for record in result.valid_records:
            writer.writerow(
                {
                    "employee_id": record.employee_id,
                    "date": record.date.isoformat(),
                    "category": record.category,
                    "amount": f"{record.amount:.2f}",
                    "description": record.description,
                    "approval_status": record.approval_status,
                    "source_row": record.source_row,
                }
            )

    return path


def write_exception_log(result: ExpenseProcessingResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_row", "employee_id", "reason", "raw_values"],
        )
        writer.writeheader()
        for issue in result.rejected_records:
            writer.writerow(
                {
                    "source_row": issue.source_row,
                    "employee_id": issue.employee_id,
                    "reason": issue.reason,
                    "raw_values": issue.raw_values,
                }
            )

    return path


def write_category_totals(result: ExpenseProcessingResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "amount"])
        writer.writeheader()
        for category, amount in sorted(result.category_totals.items()):
            writer.writerow({"category": category, "amount": f"{amount:.2f}"})

    return path


def write_report(result: ExpenseProcessingResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_summary_report(result), encoding="utf-8")
    return path
