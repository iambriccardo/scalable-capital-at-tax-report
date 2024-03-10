import json
import sys
from datetime import datetime

from currency_converter import CurrencyConverter


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


def run():
    # Path containing the configuration for the script including asset's details.
    config_path = sys.argv[1]
    # Path containing the Scalable Capital JSON dump of https://de.scalable.capital/broker/api/data.
    data_path = sys.argv[2]

    config_file = open(config_path)
    config = json.load(config_file)

    data_file = open(data_path)
    data = json.load(data_file)

    # Extract transactions from JSON data from Scalable
    transactions = data[0]["data"]["account"]["brokerPortfolios"][0]["moreTransactions"]['transactions']

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

    print("ETF Taxes Calculator\n")

    print("-- DETAILS --\n")

    print(f"Distribution equivalent income factor: {config['oekb_distribution_equivalent_income_factor']}")
    print(f"Taxes paid abroad factor: {config['oekb_taxes_paid_abroad_factor']}")
    print(f"Adjustment factor: {config['oekb_adjustment_factor']}")
    print(
        f"Exchange rate ({oekb_report_currency} -> EUR) at OEKB report {oekb_report_date.strftime('%d/%m/%Y')}: {ecb_exchange_rate}\n")

    # For each transaction we compute the quantity, share price and total price, and we filter out the ones outside
    # the time interval.
    computed_transactions = []
    for transaction in transactions:
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
    computed_transactions.insert(insertion_index, compute_adjustment_factor(config, ecb_exchange_rate))

    print("-- TRANSACTIONS --\n")

    print("Date  Quantity  Share Price  |  Total Price  Moving Average Price\n")
    for value in computed_transactions:
        # TODO: add calculation of capital gains when selling.
        # If the value is a number, it means this is an adjustment transaction.
        if isinstance(value, float):
            prev_moving_average_price = moving_average_price
            moving_average_price += value
            print(
                f"{oekb_report_date.strftime('%d/%m/%Y')}  |  Adjusting moving average price from {prev_moving_average_price} to {moving_average_price}\n")
        else:
            date, quantity, share_price, total_price = value

            moving_average_price = round(
                ((total_quantity * moving_average_price) + (quantity * share_price)) / (total_quantity + quantity), 4)

            if date <= oekb_report_date:
                total_quantity_before_report = round(total_quantity_before_report + quantity, 3)

            total_quantity = round(total_quantity + quantity, 3)

            formatted_date = date.strftime("%d/%m/%Y")
            print(
                f"{formatted_date}  |  {quantity}  {share_price}  |  {total_price}  {moving_average_price}")
            input()

    print("-- CAPITAL GAINS --\n")

    print(
        f"Distribution equivalent income (936 or 937): {compute_distribution_equivalent_income(config, ecb_exchange_rate, total_quantity_before_report)}")
    print(
        f"Taxes paid abroad (984 or 998): {compute_taxes_paid_abroad(config, ecb_exchange_rate, total_quantity_before_report)}\n")

    print("-- STATS --\n")

    print(
        f"Total shares before OKB report on {oekb_report_date.strftime('%d/%m/%Y')}: {total_quantity_before_report}")

    print(f"Total shares: {total_quantity}")


if __name__ == '__main__':
    run()
