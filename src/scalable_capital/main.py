"""Command line interface for the Austrian investment fund tax calculator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

from scalable_capital.excel_report import generate_excel_report
from scalable_capital.models import Config
from scalable_capital.tax_calculator import TaxCalculator
from scalable_capital.terminal_report import generate_terminal_report


def load_configs(config_path: Path | str) -> List[Config]:
    """Load and parse fund configurations from a JSON file."""
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        config_data = json.load(f)
    return [Config.from_dict(c) for c in config_data]


def parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config_file",
        type=Path,
        help="Path to the JSON configuration file",
    )
    parser.add_argument(
        "transactions_csv",
        type=Path,
        help="CSV export from Scalable Capital",
    )
    parser.add_argument(
        "excel_output",
        nargs="?",
        type=Path,
        help="Optional path for the Excel report",
    )
    return parser.parse_args(args)


def main(argv: Iterable[str] | None = None) -> None:
    """Run the tax calculator CLI."""
    args = parse_args(argv)

    # Validate input files
    if not args.config_file.is_file():
        raise FileNotFoundError(f"Config file not found: {args.config_file}")
    if not args.transactions_csv.is_file():
        raise FileNotFoundError(f"CSV file not found: {args.transactions_csv}")

    # Load configurations
    configs = load_configs(args.config_file)

    # Initialize and run calculator
    calculator = TaxCalculator(configs, str(args.transactions_csv))
    tax_results = calculator.calculate_taxes()

    # Generate terminal report
    generate_terminal_report(tax_results, str(args.transactions_csv))

    # Generate Excel report if requested
    if args.excel_output:
        try:
            generate_excel_report(tax_results, str(args.excel_output))
            print(f"\nExcel report generated successfully: {args.excel_output}")
        except Exception as exc:
            print(f"\nError generating Excel report: {exc}")
            sys.exit(1)


if __name__ == '__main__':
    main()
