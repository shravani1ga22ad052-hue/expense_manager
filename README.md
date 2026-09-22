# Expense Manager

Automated Expense Management & Reporting System for CSV/XLSX employee expense records.

## What it does

- Reads expense files from CSV or Excel.
- Validates dates, amounts, and approval status.
- Flags rejected and unusually large expenses.
- Produces cleaned data, summary totals, and an exception log.

## Run

```bash
python -m expense_manager.cli input_expenses.csv --output-dir output
```

## GitHub Ready Setup

Clone the repository, then install dependencies with either of these options:

```bash
pip install -r requirements.txt
```

or

```bash
pip install -e .
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

Run the website:

```bash
python -m expense_manager.webapp
```

For deployment platforms that read a Procfile, the web command is already included.

## Website Demo

Launch the presentation website with:

```bash
python -m expense_manager.webapp
```

Then open the local address shown in the terminal to upload a CSV/XLSX file or view the built-in demo dashboard.

The dashboard also includes three ready-made sample files in `src/expense_manager/static/samples/`:

- `sample_clean.csv`
- `sample_mixed.csv`
- `sample_mixed.xlsx`
- `sample_high_value.csv`

Use the manual expense form on the page if you want to type in a record during the presentation.

Or, after packaging:

```bash
expense-manager input_expenses.csv --output-dir output
```

## Outputs

- `cleaned_expenses.csv`
- `category_totals.csv`
- `monthly_expense_report.txt`
- `exception_log.csv`

## Project Layout

- `src/expense_manager/` contains the application code.
- `tests/` contains the automated checks.
