import json
import sys
import os
from datetime import datetime

from currency_converter import CurrencyConverter

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
                data_files.setdefault(name[5:], [None] * 2)[1] = open(full_path)

    # Pair config and data files with same suffix
    paired_files = []
    for suffix in sorted(set(config_files.keys()) & set(data_files.keys())):
        config = config_files[suffix][0]
        data = data_files[suffix][1]
        paired_files.append((config, data))

    return paired_files


def to_ecb_rate(ecb_exchange_rate, value):
    return round(ecb_exchange_rate * value, 4)


# Ausschüttungsgleiche Erträge 27,5% (Kennzahlen 936 oder 937)
def compute_distribution_equivalent_income(config, ecb_exchange_rate, quantity_at_report):
    return round(
        to_ecb_rate(ecb_exchange_rate, config["oekb_distribution_equivalent_income_factor"]) * quantity_at_report, 4)


# Anzurechnende ausländische (Quellen)Steuer auf Einkünfte,
# die dem besonderen Steuersatz von 27,5% unterliegen (Kennzahl 984 oder 998)
def compute_taxes_paid_abroad(config, ecb_exchange_rate, quantity_at_report):
    return round(to_ecb_rate(ecb_exchange_rate, config["oekb_taxes_paid_abroad_factor"]) * quantity_at_report, 4)


# Die Anschaffungskosten des Fondsanteils sind zu korrigieren um
def compute_adjustment_factor(config, ecb_exchange_rate):
    return round(to_ecb_rate(ecb_exchange_rate, config["oekb_adjustment_factor"]), 4)

def find_more_transactions(data):
    transactions = []

    for entry in data:
        first_portfolio = entry["data"]["account"]["brokerPortfolios"][0]
        if "moreTransactions" in first_portfolio:
            transactions.extend(first_portfolio["moreTransactions"]['transactions'])

    return transactions

def compute_taxes(config_file, data_file):
    config = json.load(config_file)
    data = json.load(data_file)

    # Extract transactions from JSON data from Scalable
    transactions = find_more_transactions(data)

    # Convert the given string date to datetime object
    start_date = datetime.strptime(config["start_date"], "%d/%m/%Y").replace(tzinfo=None)
    end_date = datetime.strptime(config["end_date"], "%d/%m/%Y").replace(tzinfo=None)
    oekb_report_date = datetime.strptime(config["oekb_report_date"], "%d/%m/%Y").replace(tzinfo=None)

    # Quantity has 3 decimal points
    # Price and factors have 4 decimal points
    total_quantity = round(config["starting_quantity"], 3)
    total_quantity_before_report = total_quantity
    moving_average_price = round(config["starting_moving_avg_price"], 4)

    # ECB exchange rate from USD to EUR
    oekb_report_currency = config.get("oekb_report_currency", "EUR")
    ecb_exchange_rate = round(
        CurrencyConverter().convert(1, oekb_report_currency, date=oekb_report_date), 4)

    print("\n\n\n -- DETAILS --\n")

    print(f"Config: {os.path.basename(config_file.name)}")
    print(f"Data: {os.path.basename(data_file.name)}\n")

    print(f"Distribution equivalent income factor: {config['oekb_distribution_equivalent_income_factor']}")
    print(f"Taxes paid abroad factor: {config['oekb_taxes_paid_abroad_factor']}")
    print(f"Adjustment factor: {config['oekb_adjustment_factor']}\n")

    print(
        f"Exchange rate ({oekb_report_currency} -> EUR) at OEKB report {oekb_report_date.strftime('%d/%m/%Y')}: {ecb_exchange_rate}")

    # For each transaction we compute the quantity, share price and total price, and we filter out the ones outside
    # the time interval.
    computed_transactions = []
    for transaction in transactions:
        if transaction["side"] != "BUY" or transaction["status"] != "SETTLED":
            print(f"\n[ERROR]: Skipping transaction with side = {transaction['side']}, status={transaction['status']}")
            continue

        date = datetime.fromisoformat(transaction['lastEventDateTime']).replace(tzinfo=None)
        quantity = transaction["quantity"]
        total_price = abs(transaction["amount"])
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

    print("\n -- TRANSACTIONS --\n")

    print("Date  Quantity  Share Price  |  Total Price  Moving Average Price\n")

    print(
        f"{config.get('start_date')}  |  {config.get('starting_quantity')}  N/A  |  N/A  {config.get('starting_moving_avg_price')}")

    for value in computed_transactions:
        # TODO: add calculation of capital gains when selling.

        # If the value is a number, it means this is an adjustment transaction. We also don't want to adjust if the
        # total quantity at the time of the report is 0.
        if isinstance(value, float) and total_quantity != 0.0:
            prev_moving_average_price = moving_average_price
            moving_average_price += value
            print(
                f"{oekb_report_date.strftime('%d/%m/%Y')}  |  Adjusting moving average price with factor {value} from {prev_moving_average_price} to {moving_average_price}")
        elif not isinstance(value, float):
            date, quantity, share_price, total_price = value

            moving_average_price = round(
                ((total_quantity * moving_average_price) + (quantity * share_price)) / (total_quantity + quantity), 4)

            if date <= oekb_report_date:
                total_quantity_before_report = round(total_quantity_before_report + quantity, 3)

            total_quantity = round(total_quantity + quantity, 3)

            formatted_date = date.strftime("%d/%m/%Y")
            print(
                f"{formatted_date}  |  {quantity}  {share_price}  |  {total_price}  {moving_average_price}")

    print("\n -- CAPITAL GAINS --\n")

    distribution_equivalent_income = compute_distribution_equivalent_income(config, ecb_exchange_rate, total_quantity_before_report)
    print(
        f"Distribution equivalent income (936 or 937): {distribution_equivalent_income}")

    taxes_paid_abroad = compute_taxes_paid_abroad(config, ecb_exchange_rate, total_quantity_before_report)
    print(
        f"Taxes paid abroad (984 or 998): {taxes_paid_abroad}")

    print("\n -- STATS --\n")

    print(
        f"Total shares before OKB report on {oekb_report_date.strftime('%d/%m/%Y')}: {total_quantity_before_report}")

    print(f"Total shares: {total_quantity}")

    return distribution_equivalent_income, taxes_paid_abroad


if __name__ == '__main__':
    folder_path = sys.argv[1]

    if not os.path.isdir(folder_path):
        print("Error: Invalid folder path.")
    else:
        paired_files = partition_files(folder_path)

        total_distribution_equivalent_income = 0
        total_taxes_paid_abroad = 0
        for config_file, data_file in paired_files:
            distribution_equivalent_income, taxes_paid_abroad = compute_taxes(config_file, data_file)
            total_distribution_equivalent_income += distribution_equivalent_income
            total_taxes_paid_abroad += taxes_paid_abroad

        print("\n -- TOTAL STATS --\n")

        # We have to round to 2 decimals since this is what Finanzonline expects.
        print(
            f"Total distribution equivalent income (936 or 937): {round(total_distribution_equivalent_income, 2)}")

        print(
            f"Total taxes paid abroad (984 or 998): {round(total_taxes_paid_abroad, 3)}\n")

        print(f"Projected taxes to pay: {round((total_distribution_equivalent_income * 0.275) - total_taxes_paid_abroad, 2)}\n")
