# Scalable Capital AT Tax Report

Austrian taxes for investments are hard and making mistakes is very easy, for this reason I created
a simple Python script which parses the data of the Scalable Capital API for an ETF and calculates all
the needed information for filing the yearly tax return (E1kv).

## Usage

1. Create a configuration file in `.json` format with the following information:
    ```json
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
      "starting_moving_avg_price": 27.927
    }
    
    ```

2. Go to your Scalable Capital asset and in the network tab copy the response of the call to
`https://de.scalable.capital/broker/api/data` where the request includes in the body the `operationName`
named `moreTransactions`.

3. Launch the script by specifying the path of the configuration and data jsons.
   ```shell
   python src/scalable_capital/main.py config_file.json data_file.json
   ```
   
## TODOs

There are still a few todos for the script:
* Add support for handling capital gains derived from selling.
* Add support for fetching OEKB data directly from their API.