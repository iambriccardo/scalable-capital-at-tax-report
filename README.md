# Scalable Capital AT Tax Report

Austrian taxes for investments are hard and making mistakes is very easy, for this reason I created
a simple Python script which parses the data of the Scalable Capital API for an ETF and calculates all
the needed information for filing the yearly tax return (E1kv).

## Usage

1. Create a configuration file in `.json` format containing an array of fund configurations:
    ```json
    [
      {
        // Date ranges in which you want to compute the report.
        "start_date": "01/01/2023",
        "end_date": "31/12/2023",
        // Data from the OEKB website for your ETF
        "oekb_report_date": "17/08/2023",
        "oekb_distribution_equivalent_income_factor": 0.8649,
        "oekb_taxes_paid_abroad_factor": 0.0723,
        "oekb_adjustment_factor": 0.7609,
        "oekb_report_currency": "USD",
        // The quantity and previously computed moving average price at the 31st december
        // of the previous year.
        "starting_quantity": 8.591,
        "starting_moving_avg_price": 27.927,
        // The ISIN of the fund
        "isin": "IE00B4L5Y983"
      }
    ]
    ```

2. Save your transaction data in a CSV file containing all transactions for all funds.

3. Launch the script by specifying both the config file and the CSV file:
   ```shell
   python src/scalable_capital/main.py path/to/config.json path/to/transactions.csv
   ```
   
## TODOs

There are still a few todos for the script:
* Add support for handling capital gains derived from selling.
* Add support for fetching OEKB data directly from their API.
* Add support for multiple reportings in a year.