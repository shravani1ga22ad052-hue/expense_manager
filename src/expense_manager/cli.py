from __future__ import annotations

import argparse
import logging
from decimal import Decimal
from pathlib import Path

from .processor import process_expenses
from .reader import read_expense_file
from .reporting import write_category_totals, write_cleaned_expenses, write_exception_log, write_report

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated expense management and reporting system")
    parser.add_argument("input_file", help="Path to the CSV or Excel expense file")
    parser.add_argument("--output-dir", default="output", help="Directory for generated reports")
    parser.add_argument("--large-threshold", default="1000.00", help="Amount that triggers a large-expense flag")
    parser.add_argument("--log-file", default="logs/expense_manager.log", help="Path to the application log file")
    return parser


def configure_logging(log_file: str | Path) -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()],
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = read_expense_file(args.input_file)
    result = process_expenses(frame, large_threshold=Decimal(args.large_threshold))

    cleaned_path = write_cleaned_expenses(result, output_dir / "cleaned_expenses.csv")
    category_totals_path = write_category_totals(result, output_dir / "category_totals.csv")
    report_path = write_report(result, output_dir / "monthly_expense_report.txt")
    exceptions_path = write_exception_log(result, output_dir / "exception_log.csv")

    LOGGER.info("Cleaned file written to %s", cleaned_path)
    LOGGER.info("Category totals written to %s", category_totals_path)
    LOGGER.info("Report written to %s", report_path)
    LOGGER.info("Exception log written to %s", exceptions_path)
    LOGGER.info("Processed %s valid expenses and %s rejected expenses", len(result.valid_records), len(result.rejected_records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
