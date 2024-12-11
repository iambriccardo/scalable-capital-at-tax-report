import json
import sys
import os
from datetime import datetime
import csv
from decimal import Decimal

from currency_converter import CurrencyConverter
from scalable_capital.models import Transaction, TransactionType, Config

def partition_files(folder_path):
    config_files = {}
    data_files = {}

    # Iterate through files in the folder
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            # Split filename into name and extension
            name, ext = os.path.splitext(filename)
            # Check if file starts with 'config_' or 'data_'
            if name.startswith('config_'):
                config_files.setdefault(name[7:], [None] * 2)[0] = open(full_path)
            elif name.startswith('data_'):
                data_files.setdefault(name[5:], [None] * 2)[1] = full_path  # Store path instead of file handle

    # Pair config and data files with same suffix
    paired_files = []
    for suffix in sorted(set(config_files.keys()) & set(data_files.keys())):
        config = config_files[suffix][0]
        data = data_files[suffix][1]  # This is now a path string
        paired_files.append((config, data))

    return paired_files


def to_ecb_rate(ecb_exchange_rate, value):
    return round(ecb_exchange_rate * value, 4)


# Ausschüttungsgleiche Erträge 27,5% (Kennzahlen 936 oder 937)
def compute_distribution_equivalent_income(config, ecb_exchange_rate, quantity_at_report):
    return round(
        to_ecb_rate(ecb_exchange_rate, config.oekb_distribution_equivalent_income_factor) * quantity_at_report, 4)


# Anzurechnende ausländische (Quellen)Steuer auf Einkünfte,
# die dem besonderen Steuersatz von 27,5% unterliegen (Kennzahl 984 oder 998)
def compute_taxes_paid_abroad(config, ecb_exchange_rate, quantity_at_report):
    return round(to_ecb_rate(ecb_exchange_rate, config.oekb_taxes_paid_abroad_factor) * quantity_at_report, 4)


# Die Anschaffungskosten des Fondsanteils sind zu korrigieren um
def compute_adjustment_factor(config, ecb_exchange_rate):
    return round(to_ecb_rate(ecb_exchange_rate, config.oekb_adjustment_factor), 4)

def find_more_transactions(csv_file_path: str) -> list[Transaction]:
    transactions = []
    
    with open(csv_file_path, 'r') as file:
        # Use semicolon as delimiter
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            transaction = Transaction.from_csv_row(row)
            transactions.append(transaction)
    
    return transactions

def compute_taxes(configs: list[Config], csv_file_path: str):
    # Extract all transactions from CSV file
    transactions = find_more_transactions(csv_file_path)
    
    total_distribution_equivalent_income = 0
    total_taxes_paid_abroad = 0

    # Process each config separately
    for config in configs:
        # Filter transactions for this specific ISIN
        isin_transactions = [t for t in transactions if t.isin == config.isin]

        # No need to parse dates anymore as they're already datetime objects
        start_date = config.start_date
        end_date = config.end_date
        oekb_report_date = config.oekb_report_date

        # Quantity has 3 decimal points
        # Price and factors have 4 decimal points
        total_quantity = round(config.starting_quantity, 3)
        total_quantity_before_report = total_quantity
        moving_average_price = round(config.starting_moving_avg_price, 4)

        # ECB exchange rate from USD to EUR
        ecb_exchange_rate = round(
            CurrencyConverter().convert(1, config.oekb_report_currency, date=oekb_report_date), 4)

        print("\n" + "="*80)
        print(f"{'DETAILS':^80}")
        print("="*80 + "\n")

        print(f"Config ISIN: {config.isin}")
        print(f"Data file: {csv_file_path}\n")

        print("OeKB Factors:")
        print(f"  • Distribution equivalent income: {config.oekb_distribution_equivalent_income_factor:.4f}")
        print(f"  • Taxes paid abroad: {config.oekb_taxes_paid_abroad_factor:.4f}")
        print(f"  • Adjustment: {config.oekb_adjustment_factor:.4f}\n")

        print(f"Exchange rate ({config.oekb_report_currency} → EUR) at {oekb_report_date.strftime('%d/%m/%Y')}: {ecb_exchange_rate:.4f}")

        # For each transaction we compute the quantity, share price and total price, and we filter out the ones outside
        # the time interval.
        computed_transactions = []
        for transaction in isin_transactions:
            if not transaction.type.is_buy() and not transaction.type.excluded():
                print(f"\n[ERROR]: Skipping transaction with type = {transaction.type.value}, status={transaction.status}")
                continue

            date = transaction.date
            quantity = float(transaction.shares)  # Convert Decimal to float for compatibility
            total_price = abs(float(transaction.amount))
            share_price = round(total_price / quantity, 4)

            if start_date <= date <= end_date:
                computed_transactions.append((date, quantity, share_price, total_price))

        # We sort the transactions in ascending date of execution.
        computed_transactions.sort(key=lambda t: t[0])

        # We insert the adjustment factor in the list of transactions.
        insertion_index = 0
        for index, value in enumerate(computed_transactions):
            if oekb_report_date >= value[0]:
                insertion_index = index + 1

        # We insert at the computed index.
        computed_transactions.insert(insertion_index, compute_adjustment_factor(config, ecb_exchange_rate))

        print("\n" + "="*80)
        print(f"{'TRANSACTIONS':^80}")
        print("="*80 + "\n")

        # Print header with proper spacing
        print(f"{'Date':12} {'Quantity':>10} {'Share Price':>12} {'Total Price':>12} {'Moving Avg':>12}")
        print("-" * 62)

        # Print starting quantity and starting moving average price
        print(f"{config.start_date.strftime('%d/%m/%Y'):12} {config.starting_quantity:>10.3f} {'N/A':>12} {'N/A':>12} {config.starting_moving_avg_price:>12.4f}")

        # Print all transactions
        for value in computed_transactions:
            if isinstance(value, float) and total_quantity != 0.0:
                prev_moving_average_price = moving_average_price
                moving_average_price += value
                print(f"\n{oekb_report_date.strftime('%d/%m/%Y')} - Adjustment: {value:+.4f} → New moving average: {moving_average_price:.4f}")
            elif not isinstance(value, float):
                date, quantity, share_price, total_price = value
                moving_average_price = round(
                    ((total_quantity * moving_average_price) + (quantity * share_price)) / (total_quantity + quantity), 4)

                if date <= oekb_report_date:
                    total_quantity_before_report = round(total_quantity_before_report + quantity, 3)

                total_quantity = round(total_quantity + quantity, 3)

                print(f"{date.strftime('%d/%m/%Y'):12} {quantity:>10.3f} {share_price:>12.4f} {total_price:>12.2f} {moving_average_price:>12.4f}")

        print("\n" + "="*80)
        print(f"{'CAPITAL GAINS':^80}")
        print("="*80 + "\n")

        distribution_equivalent_income = compute_distribution_equivalent_income(config, ecb_exchange_rate, total_quantity_before_report)
        print(f"Distribution equivalent income (936/937): {distribution_equivalent_income:>10.4f} EUR")

        taxes_paid_abroad = compute_taxes_paid_abroad(config, ecb_exchange_rate, total_quantity_before_report)
        print(f"Taxes paid abroad (984/998):             {taxes_paid_abroad:>10.4f} EUR")

        print("\n" + "="*80)
        print(f"{'STATS':^80}")
        print("="*80 + "\n")

        print(f"Total shares before OeKB report ({oekb_report_date.strftime('%d/%m/%Y')}): {total_quantity_before_report:,.3f}")
        print(f"Current total shares:                         {total_quantity:,.3f}")

        total_distribution_equivalent_income += distribution_equivalent_income
        total_taxes_paid_abroad += taxes_paid_abroad

    # Print final totals
    print("\n" + "="*80)
    print(f"{'FINAL TOTALS':^80}")
    print("="*80 + "\n")

    print(f"Total distribution equivalent income (936/937): {round(distribution_equivalent_income, 2):>10.2f} EUR")
    print(f"Total taxes paid abroad (984/998):             {round(taxes_paid_abroad, 2):>10.2f} EUR")
    print(f"Projected taxes to pay:                        {round((distribution_equivalent_income * 0.275) - taxes_paid_abroad, 2):>10.2f} EUR\n")

    return total_distribution_equivalent_income, total_taxes_paid_abroad


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python main.py <config_file> <transactions_csv>")
        sys.exit(1)

    configs_path = sys.argv[1]
    csv_path = sys.argv[2]

    if not os.path.isfile(configs_path):
        print("Error: Invalid config file path.")
        sys.exit(1)
    if not os.path.isfile(csv_path):
        print("Error: Invalid CSV file path.")
        sys.exit(1)

    # Load configs from JSON file
    with open(configs_path, 'r') as f:
        config_data = json.load(f)
        configs = [Config.from_dict(c) for c in config_data]

    distribution_equivalent_income, taxes_paid_abroad = compute_taxes(configs, csv_path)

    print("\n" + "="*80)
    print(f"{'FINAL SUMMARY':^80}")
    print("="*80 + "\n")

    # We have to round to 2 decimals since this is what Finanzonline expects.
    dei = round(distribution_equivalent_income, 2)
    tpa = round(taxes_paid_abroad, 2)
    projected = round((distribution_equivalent_income * 0.275) - taxes_paid_abroad, 2)

    print(f"{'Distribution equivalent income (936/937):':<50} {dei:>10.2f} EUR")
    print(f"{'Taxes paid abroad (984/998):':<50} {tpa:>10.2f} EUR")
    print(f"\n{'Projected taxes to pay:':<50} {projected:>10.2f} EUR")
    print("\nNote: All amounts are rounded to 2 decimal places as required by Finanzonline.")
