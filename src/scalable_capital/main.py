"""
Main entry point for the Austrian investment fund tax calculator.
Processes OeKB reports and transaction data to calculate taxable amounts.
"""
import json
import os
import sys
from typing import List

from scalable_capital.excel_report import generate_excel_report
from scalable_capital.models import Config
from scalable_capital.tax_calculator import TaxCalculator


def load_configs(config_path: str) -> List[Config]:
    """Load and parse fund configurations from JSON file."""
    with open(config_path, 'r') as f:
        config_data = json.load(f)
        return [Config.from_dict(c) for c in config_data]


def main():
    """Main entry point for the tax calculator."""
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python main.py <config_file> <transactions_csv> [excel_output]")
        print("  excel_output: Optional path for Excel report output")
        sys.exit(1)

    configs_path = sys.argv[1]
    csv_path = sys.argv[2]
    excel_path = sys.argv[3] if len(sys.argv) == 4 else None

    # Validate input files
    if not os.path.isfile(configs_path):
        print("Error: Invalid config file path.")
        sys.exit(1)
    if not os.path.isfile(csv_path):
        print("Error: Invalid CSV file path.")
        sys.exit(1)

    # Load configurations
    configs = load_configs(configs_path)

    # Initialize and run calculator
    calculator = TaxCalculator(configs, csv_path)
    tax_results = calculator.calculate_taxes()

    # Generate Excel report if requested
    if excel_path:
        try:
            generate_excel_report(tax_results, excel_path)
            print(f"\nExcel report generated successfully: {excel_path}")
        except Exception as e:
            print(f"\nError generating Excel report: {str(e)}")
            sys.exit(1)


if __name__ == '__main__':
    main()
