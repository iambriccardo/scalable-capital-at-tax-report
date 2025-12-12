# Scalable Capital AT Tax Calculator

A Python-based tool for calculating Austrian investment taxes for ETFs and stocks traded through Scalable Capital. This tool automates the complex process of calculating taxable amounts for your yearly tax return (E1kv), with special handling for accumulating ETFs and their OeKB (Oesterreichische Kontrollbank) reporting requirements.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)  
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Transaction Processing**: Automatically processes Scalable Capital transaction data
- **Tax Calculations**: Calculates distribution equivalent income (Ausschüttungsgleiche Erträge)
- **Foreign Tax Handling**: Computes foreign tax calculations and credits
- **Moving Average Tracking**: Maintains accurate moving average prices for cost basis
- **Excel Reports**: Generates detailed, audit-ready Excel reports
- **Multi-Asset Support**: Handles both accumulating ETFs and individual stocks
- **Batch Processing**: Process multiple securities in a single run
- **Currency Conversion**: Automatic ECB exchange rate integration

## Prerequisites

### System Requirements

- **Python 3.8 or higher** - [Download Python](https://www.python.org/downloads/)
- **Rye package manager** - [Install Rye](https://rye-up.com/guide/installation/)

### Required Data

Before using this tool, you'll need to gather:

1. **Scalable Capital Transaction History**
   - Export from Scalable Capital web interface
   - Navigate to "Transactions" → "Export transactions"
   - Save as CSV file containing all your transactions

2. **OeKB Report Data** (for accumulating ETFs only)
   - Visit [OeKB website](https://my.oekb.at/kapitalmaerkte-services/kms-output/fonds-info/sd/af/f)
   - Search for your ETF by ISIN
   - Note the distribution equivalent income factor and tax factors

3. **Previous Year Data**
   - Final quantities of each security as of December 31st of the previous year
   - Moving average prices for each security from the previous year

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/scalable-capital-at-tax-report
cd scalable-capital-at-tax-report
```

### Step 2: Install Dependencies

```bash
rye sync
```

This creates a virtual environment and installs all required dependencies:
- pandas (data processing)
- numpy (numerical calculations)
- currencyconverter (currency conversion)
- xlsxwriter (Excel report generation)

## Configuration

### Create Configuration File

Create a JSON configuration file (e.g., `config.json`) with your securities details:

```json
[
  {
    "start_date": "01/01/2023",
    "end_date": "31/12/2023",
    "oekb_report_date": "17/08/2023",
    "oekb_distribution_equivalent_income_factor": 0.8649,
    "oekb_taxes_paid_abroad_factor": 0.0723,
    "oekb_adjustment_factor": 0.7609,
    "oekb_report_currency": "USD",
    "starting_quantity": 8.591,
    "starting_moving_avg_price": 27.927,
    "isin": "IE00B4L5Y983",
    "security_type": "accumulating_etf"
  }
]
```

### Configuration Parameters

| Parameter | Description | Required |
|-----------|-------------|----------|
| `start_date` | Start date for tax calculation period (DD/MM/YYYY) | Yes |
| `end_date` | End date for tax calculation period (DD/MM/YYYY) | Yes |
| `isin` | ISIN code of the security | Yes |
| `security_type` | Either "accumulating_etf" or "stock" | Yes |
| `starting_quantity` | Quantity held at start of period | Yes |
| `starting_moving_avg_price` | Moving average price at start of period | Yes |
| `oekb_report_date` | OeKB report date (DD/MM/YYYY) | ETFs only |
| `oekb_distribution_equivalent_income_factor` | Distribution factor from OeKB | ETFs only |
| `oekb_taxes_paid_abroad_factor` | Foreign tax factor from OeKB | ETFs only |
| `oekb_adjustment_factor` | Adjustment factor from OeKB | ETFs only |
| `oekb_report_currency` | Currency of OeKB report | ETFs only |

## Usage

### Basic Usage

1. **Export Transaction History**
   - Log into your Scalable Capital account
   - Go to "Transactions" section
   - Click "Export transactions" and save the CSV file

2. **Run the Calculator**

   **Terminal output only:**
   ```bash
   rye run python src/scalable_capital/main.py path/to/config.json path/to/transactions.csv
   ```

   **Generate Excel report:**
   ```bash
   rye run python src/scalable_capital/main.py path/to/config.json path/to/transactions.csv output.xlsx
   ```

### Output

The tool provides:
- **Terminal Output**: Summary of calculations and key figures
- **Excel Report** (optional): Detailed breakdown with all intermediate calculations

## How It Works

This tool implements Austrian tax calculations for investment securities, with formulas and methodologies derived from extensive research across Austrian tax forums, financial communities, and official tax documentation.

### Tax Calculation Methodology

#### 1. Moving Average Price Calculation

The tool maintains a moving average cost basis for each security:

```
New Moving Average = (Current Quantity × Current Price + New Quantity × New Price) / (Current Quantity + New Quantity)
```

This moving average is crucial for calculating capital gains when securities are sold.

#### 2. Distribution Equivalent Income (Ausschüttungsgleiche Erträge)

For accumulating ETFs, calculates taxable income at 27.5% rate:

```
Distribution Equivalent Income = OeKB Factor × Quantity at Report Date × ECB Exchange Rate
```

- **OeKB Factor**: Published by Oesterreichische Kontrollbank for each ETF
- **Quantity at Report Date**: Number of shares held on the OeKB report date
- **ECB Exchange Rate**: European Central Bank rate for currency conversion

#### 3. Foreign Tax Credits (Anzurechnende ausländische Quellensteuer)

For accumulating ETFs, foreign taxes paid abroad that can be credited:

```
Foreign Tax Credit = OeKB Foreign Tax Factor × Quantity at Report Date × ECB Exchange Rate
```

#### 4. Acquisition Cost Adjustment

Accumulating ETFs require adjustment of acquisition costs:

```
Adjusted Moving Average = Current Moving Average + OeKB Adjustment Factor × ECB Exchange Rate
```

This adjustment is applied on the OeKB report date and affects all subsequent calculations.

#### 5. Capital Gains Calculation

When securities are sold, capital gains are calculated using the moving average price:

```
Capital Gain = (Sale Price - Moving Average Price) × Quantity Sold
```

### OeKB Integration

The Austrian tax authority requires specific data from OeKB for accumulating ETFs:

- **Distribution Equivalent Income Factor**: Deemed distribution per share
- **Foreign Tax Factor**: Foreign taxes paid per share
- **Adjustment Factor**: Used to adjust the acquisition cost base
- **Report Currency**: Currency in which OeKB publishes the factors

### Transaction Processing

The calculator processes various transaction types:

- **Buy Transactions**: Updates moving average price and quantity
- **Sell Transactions**: Calculates capital gains using moving average price
- **Savings Plans**: Treated as buy transactions with regular intervals
- **Adjustment Transactions**: Applied on OeKB report dates for accumulating ETFs

## Examples

### Example 1: Single ETF Configuration

```json
[
  {
    "start_date": "01/01/2023",
    "end_date": "31/12/2023",
    "oekb_report_date": "17/08/2023",
    "oekb_distribution_equivalent_income_factor": 0.8649,
    "oekb_taxes_paid_abroad_factor": 0.0723,
    "oekb_adjustment_factor": 0.7609,
    "oekb_report_currency": "USD",
    "starting_quantity": 8.591,
    "starting_moving_avg_price": 27.927,
    "isin": "IE00B4L5Y983",
    "security_type": "accumulating_etf"
  }
]
```

### Example 2: Multiple Securities Configuration

```json
[
  {
    "start_date": "01/01/2023",
    "end_date": "31/12/2023",
    "starting_quantity": 10.0,
    "starting_moving_avg_price": 85.50,
    "isin": "US0378331005",
    "security_type": "stock"
  },
  {
    "start_date": "01/01/2023",
    "end_date": "31/12/2023",
    "oekb_report_date": "17/08/2023",
    "oekb_distribution_equivalent_income_factor": 1.2345,
    "oekb_taxes_paid_abroad_factor": 0.1234,
    "oekb_adjustment_factor": 0.9876,
    "oekb_report_currency": "USD",
    "starting_quantity": 25.5,
    "starting_moving_avg_price": 42.30,
    "isin": "IE00B4L5Y983",
    "security_type": "accumulating_etf"
  }
]
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Disclaimer

**Important**: While these calculations are based on extensive research from internet sources and community knowledge, always 
consult with a qualified Austrian tax advisor for your specific situation. This tool is provided for informational purposes only 
and should not be considered as professional tax advice.

The authors are not responsible for any errors in tax calculations or compliance issues that may arise from using this tool.

---

## TODOs

- [ ] Add support for fetching OeKB data directly from their API
- [ ] Add support for multiple reportings in a year
- [ ] Add automated tests for tax calculations
- [ ] Improve error handling and validation