import json
from datetime import datetime

from currency_converter import CurrencyConverter


def to_ecb_rate(ecb_exchange_rate, value):
    return round(ecb_exchange_rate * value, 4)


# Ausschüttungsgleiche Erträge 27,5% (Kennzahlen 936 oder 937)
def compute_distribution_equivalent_income(config, ecb_exchange_rate, quantity_at_report):
    return round(to_ecb_rate(ecb_exchange_rate, config["oekb_distribution_equivalent_income_factor"]) * quantity_at_report, 4)


# Anzurechnende ausländische (Quellen)Steuer auf Einkünfte,
# die dem besonderen Steuersatz von 27,5% unterliegen (Kennzahl 984 oder 998)
def compute_taxes_paid_abroad(config, ecb_exchange_rate, quantity_at_report):
    return round(to_ecb_rate(ecb_exchange_rate, config["oekb_taxes_paid_abroad_factor"]) * quantity_at_report, 4)


# Die Anschaffungskosten des Fondsanteils sind zu korrigieren um
def compute_adjustment_factor(config, ecb_exchange_rate):
    return to_ecb_rate(ecb_exchange_rate, config["oekb_adjustment_factor"])


def run():
    paths_file = open("paths.json")
    paths = json.load(paths_file)

    config_file = open(paths["config"])
    config = json.load(config_file)

    data_file = open(paths["data"])
    data = json.load(data_file)

    # Extract transactions from JSON data
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
    ecb_exchange_rate = round(
        CurrencyConverter().convert(1, config.get("oekb_report_currency", "EUR"), date=oekb_report_date), 4)
    print(f"Using exchange rate USD -> EUR of {ecb_exchange_rate} at {oekb_report_date.strftime('%d/%m/%Y')}\n")

    # For each transaction we compute the quantity, share price and total price and we filter out the ones outside of
    # the time interval.
    computed_transactions = []
    for transaction in transactions:
        date = datetime.fromisoformat(transaction['lastEventDateTime']).replace(tzinfo=None)
        quantity = transaction["quantity"]
        total_price = abs(transaction["amount"])
        share_price = round(total_price / quantity, 4)

        if start_date <= date <= end_date:
            computed_transactions.append((date, quantity, share_price, total_price))

    computed_transactions.sort(key=lambda t: t[0])

    # We insert the adjustment factor in the list of transactions.
    insertion_index = 0
    for index, value in enumerate(computed_transactions):
        if oekb_report_date >= value[0]:
            insertion_index = index + 1
    computed_transactions.insert(insertion_index, compute_adjustment_factor(config, ecb_exchange_rate))

    print("Date  Quantity  Share Price  |  Total Price  Moving Average Price\n")
    for value in computed_transactions:
        # TODO: add calculation of capital gains when selling.
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
        f"Taxes paid abroad (984 or 998): {compute_taxes_paid_abroad(config, ecb_exchange_rate, total_quantity_before_report)}")

    print("")

    print("-- STATS --\n")
    print(
        f"Total shares before OKB report on {oekb_report_date.strftime('%d/%m/%Y')}: {total_quantity_before_report}")

    print(f"Total shares: {total_quantity}")


if __name__ == '__main__':
    run()
