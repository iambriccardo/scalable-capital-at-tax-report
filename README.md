# Scalable Capital AT Tax Calculator

A Python-based tool for calculating Austrian investment taxes for ETFs and stocks traded through Scalable Capital. This tool helps automate the complex process of calculating taxable amounts for your yearly tax return (E1kv), with special handling for accumulating ETFs and their OeKB (Oesterreichische Kontrollbank) reporting requirements.

## Features

- Processes Scalable Capital transaction data
- Calculates distribution equivalent income (Ausschüttungsgleiche Erträge)
- Handles foreign tax calculations
- Computes moving average prices
- Generates detailed Excel reports
- Supports both accumulating ETFs and stocks
- Handles multiple securities in a single run

## Prerequisites

Before using this tool, you'll need:

1. Python 3.8 or higher installed on your computer
2. [Rye](https://rye-up.com/) package manager installed
3. The following transaction data and information:
   - Your Scalable Capital transaction history exported as CSV (using the "Export transactions" feature in Scalable Capital's web interface)
   - OeKB report data for your accumulating ETFs (from [OeKB website](https://my.oekb.at/kapitalmaerkte-services/kms-output/fonds-info/sd/af/f))
   - Previous year's final quantities and moving average prices for your securities

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/scalable-capital-at-tax
   cd scalable-capital-at-tax
   ```

2. Install dependencies using Rye:
   ```bash
   rye sync
   ```

## Configuration

1. Create a JSON configuration file (e.g., `config.json`) with your fund details:
    ```json
    [
      {
        // Date ranges in which you want to compute the report.
        "start_date": "01/01/2023",
        "end_date": "31/12/2023",
        // Data from the OEKB website for your ETF (not needed for stocks)
        "oekb_report_date": "17/08/2023",
        "oekb_distribution_equivalent_income_factor": 0.8649,
        "oekb_taxes_paid_abroad_factor": 0.0723,
        "oekb_adjustment_factor": 0.7609,
        "oekb_report_currency": "USD",
        // The quantity and previously computed moving average price at the 31st december
        // of the previous year.
        "starting_quantity": 8.591,
        "starting_moving_avg_price": 27.927,
        // The ISIN of the security
        "isin": "IE00B4L5Y983",
        // The security type (either "accumulating_etf" or "stock")
        "security_type": "accumulating_etf"
      }
    ]
    ```

2. Save your transaction data in a CSV file containing all transactions for all funds.

## Usage

1. Export your transaction history from Scalable Capital:
   - Log into your Scalable Capital account
   - Go to the "Transactions" section
   - Click on "Export transactions" and save the CSV file

2. Save your transaction data CSV file in a convenient location.

3. Launch the script using Rye. You have two output options:
   ```shell
   # For terminal output only:
   rye run python src/scalable_capital/main.py path/to/config.json path/to/transactions.csv

   # To generate an Excel report in addition to terminal output:
   rye run python src/scalable_capital/main.py path/to/config.json path/to/transactions.csv output.xlsx
   ```

   The Excel report will contain detailed calculations and breakdowns that can be useful for record-keeping and verification purposes.

## TODOs

There are still a few todos for the script:
* Add support for fetching OEKB data directly from their API.
* Add support for multiple reportings in a year.