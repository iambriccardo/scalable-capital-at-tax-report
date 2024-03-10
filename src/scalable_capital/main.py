import json
from datetime import datetime

if __name__ == '__main__':
    config_file = open("config.json")
    config = json.load(config_file)

    data_file = open(config["scalable_capital_json"])
    data = json.load(data_file)

    # Extract transactions from JSON data
    transactions = data[0]["data"]["account"]["brokerPortfolios"][0]["moreTransactions"]['transactions']

    # Convert the given string date to datetime object
    start_date = datetime.strptime(config["start_date"], "%d/%m/%Y").replace(tzinfo=None)
    end_date = datetime.strptime(config["end_date"], "%d/%m/%Y").replace(tzinfo=None)
    oekb_report_date = datetime.strptime(config["oekb_report_date"], "%d/%m/%Y").replace(tzinfo=None)

    total_quantity = config["starting_quantity"]
    total_quantity_before_report = total_quantity
    moving_average_price = config["starting_moving_avg_price"]

    # For each transaction we compute the quantity, share price and total price and we filter out the ones outside of
    # the time interval.
    computed_transactions = []
    for transaction in transactions:
        date = datetime.fromisoformat(transaction['lastEventDateTime']).replace(tzinfo=None)
        quantity = transaction["quantity"]
        total_price = abs(transaction["amount"])
        share_price = round(total_price / quantity, 3)

        if start_date <= date <= end_date:
            computed_transactions.append((date, quantity, share_price, total_price))

    computed_transactions.sort(key=lambda t: t[0])

    print("Date  Quantity  Share Price  |  Total Price  Moving Average Price\n")
    for date, quantity, share_price, total_price in computed_transactions:
        moving_average_price = ((total_quantity * moving_average_price) + (quantity * share_price)) / (total_quantity + quantity)

        if date <= oekb_report_date:
            total_quantity_before_report += quantity

        total_quantity += quantity

        formatted_date = date.strftime("%d/%m/%Y")
        print(f"{formatted_date}  {round(quantity, 3)}  {share_price}  |  {round(total_price, 4)}  {round(moving_average_price, 4)}")
        input()

    print(f"Total shares before OKB report on {oekb_report_date.strftime('%d/%m/%Y')}: {round(total_quantity_before_report, 3)}")
    print(f"Total shares: {round(total_quantity, 3)}")
