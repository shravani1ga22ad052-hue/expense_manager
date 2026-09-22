from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class ExpenseRecord:
    employee_id: str
    date: date
    category: str
    amount: Decimal
    description: str
    approval_status: str
    source_row: int


@dataclass(slots=True)
class ExpenseIssue:
    source_row: int
    employee_id: str
    reason: str
    raw_values: dict[str, object]


@dataclass(slots=True)
class ExpenseProcessingResult:
    valid_records: list[ExpenseRecord]
    rejected_records: list[ExpenseIssue]
    large_expenses: list[ExpenseRecord]
    employee_totals: dict[str, Decimal]
    category_totals: dict[str, Decimal]
    monthly_totals: dict[str, Decimal]
    employee_category_totals: dict[str, dict[str, Decimal]]
