"""
Main entry point for the Austrian investment fund tax calculator.
Processes OeKB reports and transaction data to calculate taxable amounts.
"""
import json
import os
import sys
from typing import List

from scalable_capital.models import Config
from scalable_capital.tax_calculator import TaxCalculator


def load_configs(config_path: str) -> List[Config]:
    """Load and parse fund configurations from JSON file."""
    with open(config_path, 'r') as f:
        config_data = json.load(f)
        return [Config.from_dict(c) for c in config_data]


def main():
    """Main entry point for the tax calculator."""
    if len(sys.argv) != 3:
        print("Usage: python main.py <config_file> <transactions_csv>")
        sys.exit(1)

    configs_path = sys.argv[1]
    csv_path = sys.argv[2]

    # Validate input files
    if not os.path.isfile(configs_path):
        print("Error: Invalid config file path.")
        sys.exit(1)
    if not os.path.isfile(csv_path):
        print("Error: Invalid CSV file path.")
        sys.exit(1)

    # Initialize and run calculator
    configs = load_configs(configs_path)
    calculator = TaxCalculator(configs, csv_path)
    calculator.calculate_taxes()


if __name__ == '__main__':
    main()
