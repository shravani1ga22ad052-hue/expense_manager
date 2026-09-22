from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
from flask import Flask, flash, render_template, request, session

from .processor import process_expenses
from .reader import read_expense_file
from .reader import REQUIRED_COLUMNS
from .reporting import format_currency

APP_TITLE = "Expense Manager Showcase"
MAX_UPLOAD_SIZE = 8 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MANUAL_ENTRIES_SESSION_KEY = "manual_expense_entries"
SAMPLE_FILES = [
    {"label": "Clean sample dataset", "file": "samples/sample_clean.csv"},
    {"label": "Mixed quality dataset", "file": "samples/sample_mixed.csv"},
    {"label": "Mixed quality dataset (Excel)", "file": "samples/sample_mixed.xlsx"},
    {"label": "High-value expense dataset", "file": "samples/sample_high_value.csv"},
    {"label": "Presentation-friendly demo", "file": "samples/sample_presentation_friendly.csv"},
]

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "expense-manager-demo"
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


def _build_demo_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "employee_id": "E102",
                "date": "2026-09-03",
                "category": "Travel",
                "amount": 1240.00,
                "description": "Client presentation flight",
                "approval_status": "approved",
            },
            {
                "employee_id": "E102",
                "date": "2026-09-05",
                "category": "Meals",
                "amount": 58.40,
                "description": "Team dinner after demo",
                "approval_status": "approved",
            },
            {
                "employee_id": "E204",
                "date": "2026-09-08",
                "category": "Software",
                "amount": 399.00,
                "description": "Monthly subscription renewal",
                "approval_status": "approved",
            },
            {
                "employee_id": "E204",
                "date": "2026-09-10",
                "category": "Office",
                "amount": 92.15,
                "description": "Conference materials",
                "approval_status": "rejected",
            },
            {
                "employee_id": "E307",
                "date": "2026-09-14",
                "category": "Travel",
                "amount": 780.00,
                "description": "Regional partner visit",
                "approval_status": "approved",
            },
            {
                "employee_id": "E307",
                "date": "2026-09-18",
                "category": "Training",
                "amount": 215.00,
                "description": "Team workshop registration",
                "approval_status": "approved",
            },
        ]
    )


def _file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _load_uploaded_frame(upload) -> pd.DataFrame:
    data = upload.read()
    filename = upload.filename or ""
    suffix = _file_extension(filename)

    if suffix == ".csv":
        return pd.read_csv(BytesIO(data))
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(data))
    raise ValueError("Please upload a CSV or Excel expense file.")


def _manual_entries() -> list[dict[str, str]]:
    entries = session.get(MANUAL_ENTRIES_SESSION_KEY, [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _manual_entries_frame() -> pd.DataFrame:
    entries = _manual_entries()
    if not entries:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.DataFrame(entries, columns=REQUIRED_COLUMNS)


def _parse_manual_entry(form) -> dict[str, str]:
    employee_id = str(form.get("manual_employee_id", "")).strip()
    expense_date = str(form.get("manual_date", "")).strip()
    category = str(form.get("manual_category", "")).strip()
    amount = str(form.get("manual_amount", "")).strip()
    description = str(form.get("manual_description", "")).strip()
    approval_status = str(form.get("manual_approval_status", "")).strip()

    if not all([employee_id, expense_date, category, amount, description, approval_status]):
        raise ValueError("Fill in every manual expense field before adding it.")

    return {
        "employee_id": employee_id,
        "date": expense_date,
        "category": category,
        "amount": amount,
        "description": description,
        "approval_status": approval_status,
    }


def _build_dashboard_context(frame: pd.DataFrame, source_name: str) -> dict[str, object]:
    result = process_expenses(frame)
    total_spend = sum(result.employee_totals.values(), Decimal("0.00"))
    largest_expense = max((record.amount for record in result.valid_records), default=Decimal("0.00"))
    top_employee = max(result.employee_totals.items(), key=lambda item: item[1], default=("N/A", Decimal("0.00")))

    category_rows = [
        {"name": category, "amount": amount, "percentage": (amount / total_spend * 100) if total_spend else 0}
        for category, amount in sorted(result.category_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    monthly_rows = [
        {"month": month, "amount": amount}
        for month, amount in sorted(result.monthly_totals.items())
    ]
    issue_rows = [
        {
            "row": issue.source_row,
            "employee_id": issue.employee_id or "Unknown",
            "reason": issue.reason,
        }
        for issue in result.rejected_records[:6]
    ]

    return {
        "app_title": APP_TITLE,
        "source_name": source_name,
        "result": result,
        "total_spend": total_spend,
        "largest_expense": largest_expense,
        "top_employee": top_employee,
        "category_rows": category_rows,
        "monthly_rows": monthly_rows,
        "issue_rows": issue_rows,
        "format_currency": format_currency,
        "sample_files": SAMPLE_FILES,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    uploaded = request.files.get("expense_file")
    action = request.form.get("action", "")
    source_name = "Built-in demo dataset"

    if request.method == "POST" and action == "manual_clear":
        session.pop(MANUAL_ENTRIES_SESSION_KEY, None)
        flash("Manual entries cleared.", "success")

    if request.method == "POST" and action == "manual_add":
        try:
            manual_entry = _parse_manual_entry(request.form)
            entries = _manual_entries()
            entries.append(manual_entry)
            session[MANUAL_ENTRIES_SESSION_KEY] = entries
            flash("Manual expense added to the dashboard.", "success")
        except Exception as exc:
            flash(str(exc), "error")

    manual_frame = _manual_entries_frame()
    combined_frame = _build_demo_frame() if manual_frame.empty else pd.concat([_build_demo_frame(), manual_frame], ignore_index=True)

    if request.method == "POST":
        if action == "upload_file":
            if uploaded is None or not uploaded.filename:
                flash("Choose a CSV or Excel file to upload.", "warning")
            else:
                try:
                    if _file_extension(uploaded.filename) not in ALLOWED_EXTENSIONS:
                        raise ValueError("Upload a CSV or Excel file.")
                    frame = _load_uploaded_frame(uploaded)
                    source_name = uploaded.filename
                    context = _build_dashboard_context(frame, source_name)
                    context["upload_name"] = uploaded.filename
                    context["manual_count"] = len(_manual_entries())
                    return render_template("index.html", **context)
                except Exception as exc:
                    flash(str(exc), "error")
        elif action not in {"manual_add", "manual_clear"}:
            if uploaded is None or not uploaded.filename:
                flash("Choose a CSV or Excel file to upload, or add a manual expense.", "warning")
            else:
                try:
                    if _file_extension(uploaded.filename) not in ALLOWED_EXTENSIONS:
                        raise ValueError("Upload a CSV or Excel file.")
                    frame = _load_uploaded_frame(uploaded)
                    source_name = uploaded.filename
                    context = _build_dashboard_context(frame, source_name)
                    context["upload_name"] = uploaded.filename
                    context["manual_count"] = len(_manual_entries())
                    return render_template("index.html", **context)
                except Exception as exc:
                    flash(str(exc), "error")

    context = _build_dashboard_context(combined_frame, source_name)
    context["upload_name"] = None
    context["manual_count"] = len(_manual_entries())
    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
