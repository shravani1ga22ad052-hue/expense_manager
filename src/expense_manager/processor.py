from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from .models import ExpenseIssue, ExpenseProcessingResult, ExpenseRecord
from .reader import REQUIRED_COLUMNS

REJECTED_STATUSES = {
    "rejected",
    "declined",
    "denied",
    "not approved",
    "disapproved",
}

APPROVED_STATUSES = {
    "approved",
    "yes",
    "y",
    "true",
    "submitted",
}

ZERO = Decimal("0.00")
TWOPLACES = Decimal("0.01")


def _normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _parse_date(value: object) -> date:
    if value is None or pd.isna(value):
        raise ValueError("Date is missing")
    try:
        parsed = pd.to_datetime(value, errors="raise")
    except Exception as exc:
        raise ValueError("Date must be in a valid format (for example, 2026-09-22)") from exc
    return parsed.date()


def _parse_amount(value: object) -> Decimal:
    if value is None or pd.isna(value):
        raise ValueError("Amount is missing")

    cleaned = str(value).strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Amount must be a valid number") from exc

    if amount <= ZERO:
        raise ValueError("Amount must be greater than 0")

    return amount.quantize(TWOPLACES)


def _blank_totals() -> tuple[dict[str, Decimal], dict[str, Decimal], dict[str, Decimal], dict[str, dict[str, Decimal]]]:
    return {}, {}, {}, {}


def process_expenses(frame: pd.DataFrame, large_threshold: Decimal | str | float = Decimal("1000.00")) -> ExpenseProcessingResult:
    if isinstance(large_threshold, str):
        threshold = Decimal(large_threshold)
    else:
        threshold = Decimal(str(large_threshold))

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    valid_records: list[ExpenseRecord] = []
    rejected_records: list[ExpenseIssue] = []
    large_expenses: list[ExpenseRecord] = []

    employee_totals, category_totals, monthly_totals, employee_category_totals = _blank_totals()

    for index, row in frame.iterrows():
        source_row = int(index) + 2
        raw_values = {column: row[column] for column in REQUIRED_COLUMNS}

        try:
            employee_id = _normalize_text(row["employee_id"])
            if not employee_id:
                raise ValueError("Employee ID is missing")

            approval_status = _normalize_text(row["approval_status"]).lower()
            if not approval_status:
                raise ValueError("Approval status is missing")

            expense_date = _parse_date(row["date"])
            amount = _parse_amount(row["amount"])
            category = _normalize_text(row["category"]) or "Uncategorized"
            description = _normalize_text(row["description"])

            if approval_status in REJECTED_STATUSES:
                rejected_records.append(
                    ExpenseIssue(
                        source_row=source_row,
                        employee_id=employee_id,
                        reason=f"Expense rejected by approval status: {approval_status}",
                        raw_values=raw_values,
                    )
                )
                continue

            record = ExpenseRecord(
                employee_id=employee_id,
                date=expense_date,
                category=category,
                amount=amount,
                description=description,
                approval_status=approval_status,
                source_row=source_row,
            )
            valid_records.append(record)

            employee_totals[employee_id] = employee_totals.get(employee_id, ZERO) + amount
            category_totals[category] = category_totals.get(category, ZERO) + amount
            month_key = expense_date.strftime("%Y-%m")
            monthly_totals[month_key] = monthly_totals.get(month_key, ZERO) + amount
            employee_category_totals.setdefault(employee_id, {})[category] = (
                employee_category_totals.setdefault(employee_id, {}).get(category, ZERO) + amount
            )

            if amount >= threshold:
                large_expenses.append(record)

        except Exception as exc:
            rejected_records.append(
                ExpenseIssue(
                    source_row=source_row,
                    employee_id=_normalize_text(row.get("employee_id", "")),
                    reason=str(exc),
                    raw_values=raw_values,
                )
            )

    return ExpenseProcessingResult(
        valid_records=valid_records,
        rejected_records=rejected_records,
        large_expenses=large_expenses,
        employee_totals=employee_totals,
        category_totals=category_totals,
        monthly_totals=monthly_totals,
        employee_category_totals=employee_category_totals,
    )
