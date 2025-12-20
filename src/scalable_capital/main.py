"""
Main entry point for the Austrian investment fund tax calculator.
Processes OeKB reports and transaction data to calculate taxable amounts.
"""
import json
import os
import sys
import csv
from typing import List

from scalable_capital.excel_report import generate_excel_report
from scalable_capital.models import Config
from scalable_capital.tax_calculator import TaxCalculator
from scalable_capital.terminal_report import generate_terminal_report
from scalable_capital.json_converter import convert_json_to_csv
from scalable_capital.constants import DEFAULT_FILE_ENCODING, CSV_DELIMITER, CSV_PREVIEW_LINES
from scalable_capital.exceptions import ConfigurationError, FileConversionError


def load_configs(config_path: str) -> List[Config]:
    """
    Load and parse fund configurations from JSON file.

    Args:
        config_path: Path to the JSON configuration file

    Returns:
        List of Config objects

    Raises:
        ConfigurationError: If the configuration file is invalid
    """
    try:
        with open(config_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
            config_data = json.load(f)
            return [Config.from_dict(c) for c in config_data]
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise ConfigurationError(f"Invalid configuration file: {str(e)}") from e


def is_json_file(file_path: str) -> bool:
    """
    Check if a file is a JSON file based on extension and content.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file is JSON format, False otherwise
    """
    if file_path.lower().endswith('.json'):
        return True
    # Also try to detect by parsing
    try:
        with open(file_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def display_csv_preview(csv_path: str, max_rows: int = None):
    """
    Display a preview of the CSV file with fee information highlighted.

    Args:
        csv_path: Path to the CSV file
        max_rows: Maximum number of rows to display (None for all rows)
    """
    print("\n" + "=" * 140)
    if max_rows:
        print("CSV PREVIEW (first {} rows):".format(max_rows))
    else:
        print("CSV PREVIEW (all rows):")
    print("=" * 140)
    print(f"Reading from: {os.path.abspath(csv_path)}")
    print("-" * 140)

    with open(csv_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
        reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
        rows = list(reader)

        if not rows:
            print("(empty file)")
            return

        # Check for transactions with fees
        transactions_with_fees = []
        for row in rows:
            fee_value = row.get('fee', '0,00').replace(',', '.')
            try:
                if float(fee_value) > 0:
                    transactions_with_fees.append({
                        'date': row.get('date', 'N/A'),
                        'description': row.get('description', 'N/A'),
                        'amount': row.get('amount', 'N/A'),
                        'fee': row.get('fee', 'N/A'),
                        'type': row.get('type', 'N/A')
                    })
            except ValueError:
                pass

        # Print header
        headers = list(rows[0].keys())
        header_line = " | ".join(f"{h[:12]:12}" for h in headers)
        print(header_line)
        print("-" * len(header_line))

        # Print rows (all or limited)
        rows_to_display = rows[:max_rows] if max_rows else rows
        for i, row in enumerate(rows_to_display):
            values = [str(row[h])[:12] for h in headers]
            line = " | ".join(f"{v:12}" for v in values)
            print(line)

        if max_rows and len(rows) > max_rows:
            print(f"\n... and {len(rows) - max_rows} more rows")

        print(f"\nTotal transactions: {len(rows)}")

        # Display fee summary if any fees exist
        if transactions_with_fees:
            print("\n" + "=" * 140)
            print("TRANSACTIONS WITH FEES - AMOUNT CALCULATION")
            print("=" * 140)
            print("\nThe following transactions had fees that were adjusted:")
            print("-" * 140)
            print(f"{'Date':<12} {'Type':<10} {'Description':<40} {'JSON Amount':>15} {'Fee':>10} {'CSV Amount':>15}")
            print("-" * 140)
            for tx in transactions_with_fees:
                # Parse the amounts to show calculation
                csv_amount_str = tx['amount']
                fee_str = tx['fee']

                # Convert to float for calculation display
                try:
                    csv_amount = float(csv_amount_str.replace(',', '.'))
                    fee = float(fee_str.replace(',', '.'))
                    json_amount = csv_amount - fee
                    json_amount_str = f"{json_amount:.2f}".replace('.', ',')
                except:
                    json_amount_str = "N/A"

                print(f"{tx['date']:<12} {tx['type']:<10} {tx['description'][:40]:<40} {json_amount_str:>15} {fee_str:>10} {csv_amount_str:>15}")

            print("-" * 140)
            print(f"\nTotal transactions with fees: {len(transactions_with_fees)}")
            print("\nCalculation: CSV Amount = JSON Amount + Fee")
            print("  - For BUY:  JSON amount includes the fee (you paid share_value + fee)")
            print("  - For SELL: JSON amount excludes the fee (you received proceeds - fee)")
            print("  - CSV shows the gross amount (share value for tax purposes) and fee separately")
            print("=" * 140)

    print("=" * 140)


def get_user_confirmation(prompt: str = "Do you want to continue?") -> bool:
    """
    Ask user for confirmation with yes/no response.

    Args:
        prompt: The question to ask the user

    Returns:
        True if user confirms, False otherwise
    """
    while True:
        response = input(f"\n{prompt} (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def handle_json_conversion(json_path: str) -> str:
    """
    Convert JSON file to CSV and get user confirmation.

    Args:
        json_path: Path to the JSON file

    Returns:
        Path to the generated CSV file

    Raises:
        SystemExit: If user cancels the operation
    """
    # Generate output CSV path
    base_name = os.path.splitext(json_path)[0]
    csv_output_path = f"{base_name}_converted.csv"
    csv_absolute_path = os.path.abspath(csv_output_path)

    print("\n" + "=" * 140)
    print("JSON FILE DETECTED")
    print("=" * 140)
    print(f"\nInput JSON file: {os.path.abspath(json_path)}")
    print(f"Converting to CSV format...")

    try:
        # Convert JSON to CSV
        num_transactions = convert_json_to_csv(json_path, csv_output_path)

        print(f"✓ Conversion successful!")
        print(f"✓ Converted {num_transactions} transactions")
        print(f"\n📁 Output CSV location:")
        print(f"   {csv_absolute_path}")

        # Display preview
        display_csv_preview(csv_output_path)

        # Ask for confirmation
        if not get_user_confirmation("Does the CSV look correct? Continue with tax calculation?"):
            print("\nOperation cancelled by user.")
            print(f"\n📁 The converted CSV has been saved at:")
            print(f"   {csv_absolute_path}")
            print("\nYou can review it and run the tax calculator manually if needed:")
            print(f"   rye run python src/scalable_capital/main.py <config.json> {csv_output_path}")
            sys.exit(0)

        return csv_output_path

    except Exception as e:
        raise FileConversionError(f"Error converting JSON to CSV: {str(e)}") from e


def main():
    """
    Main entry point for the tax calculator.

    Processes command-line arguments, converts JSON to CSV if needed,
    calculates taxes, and generates reports.

    Exits with status 1 on error.
    """
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python main.py <config_file> <transactions_file> [excel_output]")
        print("\n  transactions_file: Can be either CSV or JSON format")
        print("    - CSV: Direct Scalable Capital export")
        print("    - JSON: API response from Scalable Capital")
        print("  excel_output: Optional path for Excel report output")
        sys.exit(1)

    configs_path = sys.argv[1]
    transactions_file = sys.argv[2]
    excel_path = sys.argv[3] if len(sys.argv) == 4 else None

    # Validate config file
    if not os.path.isfile(configs_path):
        print(f"Error: Config file not found: {configs_path}")
        sys.exit(1)

    # Validate transactions file
    if not os.path.isfile(transactions_file):
        print(f"Error: Transactions file not found: {transactions_file}")
        sys.exit(1)

    try:
        # Detect file type and handle JSON conversion if needed
        if is_json_file(transactions_file):
            csv_path = handle_json_conversion(transactions_file)
            print("\n✓ Proceeding with tax calculation...\n")
        else:
            csv_path = transactions_file

        # Load configurations
        configs = load_configs(configs_path)

        # Initialize and run calculator
        calculator = TaxCalculator(configs, csv_path)
        tax_results = calculator.calculate_taxes()

        # Generate terminal report
        generate_terminal_report(tax_results, csv_path)

        # Generate Excel report if requested
        if excel_path:
            generate_excel_report(tax_results, excel_path)
            print(f"\nExcel report generated successfully: {excel_path}")

    except (ConfigurationError, FileConversionError) as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
