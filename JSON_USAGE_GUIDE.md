# JSON Support Usage Guide

This guide explains how to use the JSON import feature to process transactions directly from the Scalable Capital API.

## Getting Your Transaction Data (JSON)

### From Scalable Capital API

1. **Log in to Scalable Capital** in your web browser
2. **Navigate to the API endpoint**: `https://de.scalable.capital/broker/api/data`
3. **Copy the JSON response**:
   - The page will display raw JSON data
   - Press `Ctrl+A` (Windows/Linux) or `Cmd+A` (Mac) to select all
   - Press `Ctrl+C` (Windows/Linux) or `Cmd+C` (Mac) to copy
4. **Save to a file**:
   - Open a text editor (Notepad, TextEdit, VS Code, etc.)
   - Paste the JSON data (`Ctrl+V` or `Cmd+V`)
   - Save as `transactions.json` (or any name ending in `.json`)

**That's it!** No need to modify or format the JSON - just copy and paste as-is.

> **Note**: You must be logged in to your Scalable Capital account to access this API endpoint. If you're not logged in, the page will redirect you to the login page.

## Quick Start

The tax calculator now supports both CSV and JSON input files:

```bash
# Using CSV (traditional method)
rye run python src/scalable_capital/main.py config.json transactions.csv

# Using JSON (new method - automatic conversion)
rye run python src/scalable_capital/main.py config.json transactions.json
```

## Why Use JSON?

- **Direct API Access**: Copy transactions directly from Scalable Capital API responses
- **No Manual Export**: Skip the CSV export step from the web interface
- **Automatic Conversion**: The tool handles the conversion to CSV format
- **Smart Filtering**: Automatically excludes cash transactions (deposits, fees, etc.) - only includes security trades
- **Verification**: Preview the converted data before processing
- **Reusability**: Converted CSV is saved for future use

## How It Works

### Step-by-Step Workflow

1. **Obtain JSON Data from API**
   - Open your browser and navigate to: `https://de.scalable.capital/broker/api/data`
   - Copy the entire JSON response from the API endpoint
   - Save it to a file (e.g., `my_transactions.json`)

   **Important**: Simply copy-paste the raw JSON response as-is, no modifications needed!

2. **Run the Tax Calculator**
   ```bash
   rye run python src/scalable_capital/main.py config.json my_transactions.json
   ```

3. **Automatic Detection**
   ```
   ============================================================================
   JSON FILE DETECTED
   ============================================================================

   Input JSON file: my_transactions.json
   Converting to CSV format...
   ```

4. **Conversion & Preview**
   ```
   (Skipped 34 cash transactions - only security transactions are included)
   ✓ Conversion successful!
   ✓ Converted 16 transactions

   📁 Output CSV location:
      /full/path/to/my_transactions_converted.csv

   ============================================================================
   CSV PREVIEW (all rows):
   ============================================================================
   Reading from: /full/path/to/my_transactions_converted.csv
   ----------------------------------------------------------------------------
   date         | time     | status   | type         | isin         | shares
   2025-03-10   | 10:33:23 | Executed | Savings plan | IE00BK5BQT80 | 6,234
   2025-02-10   | 10:08:59 | Executed | Savings plan | IE00BK5BQT80 | 5,837
   2025-01-10   | 10:07:15 | Executed | Savings plan | IE00BK5BQT80 | 5,99
   ... (all 16 rows shown)

   Total transactions: 16
   ```

5. **User Confirmation**
   ```
   Does the CSV look correct? Continue with tax calculation? (yes/no):
   ```

   - Type `yes` or `y` to proceed with tax calculation
   - Type `no` or `n` to cancel (CSV will still be saved)

6. **Tax Calculation**
   If you confirm, the tool proceeds with normal tax calculation using the converted CSV.

## What the API Response Looks Like

When you navigate to `https://de.scalable.capital/broker/api/data`, you'll see raw JSON that starts like this:

```json
[
    {
        "data": {
            "account": {
                "id": "...",
                "brokerPortfolio": {
                    "id": "...",
                    "moreTransactions": {
                        "cursor": "...",
                        "total": 50,
                        "transactions": [
                            ...
```

This is exactly what you should copy and save!

## JSON Format Expected

The tool expects JSON in the following structure (from Scalable Capital API `https://de.scalable.capital/broker/api/data`):

```json
[
    {
        "data": {
            "account": {
                "brokerPortfolio": {
                    "moreTransactions": {
                        "transactions": [
                            {
                                "id": "transaction_id",
                                "type": "SECURITY_TRANSACTION",
                                "status": "SETTLED",
                                "lastEventDateTime": "2025-03-10T10:33:23.220Z",
                                "description": "Vanguard FTSE All-World (Acc)",
                                "securityTransactionType": "SAVINGS_PLAN",
                                "quantity": 6.234,
                                "amount": -799.9469,
                                "side": "BUY",
                                "isin": "IE00BK5BQT80",
                                "currency": "EUR"
                            }
                        ]
                    }
                }
            }
        }
    }
]
```

## Supported Transaction Types

The converter **only includes security transactions** that are relevant for tax calculations:

### Included: Security Transactions
- **Savings Plans** → `Savings plan`
- **Buy Orders** → `Buy`
- **Sell Orders** → `Sell`

### Included: Non-Trade Security Transactions
- **Transfer In** → `Buy`
- **Transfer Out** → `Sell`

### Excluded: Cash Transactions (Not Needed for Tax Calculation)
- ❌ **Deposits** - Skipped
- ❌ **Withdrawals** - Skipped
- ❌ **Fees** - Skipped
- ❌ **Interest** - Skipped

> **Note**: Cash transactions are automatically filtered out because they're not needed for calculating capital gains or distribution equivalent income. The tool will inform you how many cash transactions were skipped during conversion.

## Field Mapping

The converter automatically maps JSON fields to CSV columns:

| JSON Field | CSV Column | Notes |
|------------|------------|-------|
| `lastEventDateTime` | `date`, `time` | Split into separate fields |
| `quantity` | `shares` | Formatted with comma decimal separator |
| `amount` | `amount` | Formatted with comma decimal separator |
| `amount / quantity` | `price` | Calculated automatically, 2 decimals |
| `status` (SETTLED) | `status` (Executed) | Mapped for compatibility |
| `isin` | `isin` | Direct copy |
| `description` | `description` | Direct copy |
| `currency` | `currency` | Direct copy |

## Output Files

When you run with a JSON file, two files are created/used:

1. **Converted CSV**: `<json_filename>_converted.csv`
   - Automatically generated from JSON
   - Compatible with tax calculator
   - Saved in the same directory as the JSON file
   - Can be reused for future calculations

2. **Excel Report** (optional): Specified by you
   ```bash
   rye run python src/scalable_capital/main.py config.json data.json report.xlsx
   ```

## Verification

The conversion process ensures data accuracy:

✓ **Quantity/Shares**: Exact match from JSON
✓ **Price Calculation**: `price = |amount| / quantity`
✓ **Amount**: Exact match from JSON
✓ **Decimal Format**: European format (comma separator)
✓ **Transaction Types**: Properly mapped
✓ **Status Codes**: Correctly translated

## Examples

### Example 1: Basic JSON Workflow

```bash
# You have: transactions.json (from API)
# You need: config.json (your securities configuration)

rye run python src/scalable_capital/main.py config.json transactions.json

# Output:
# - Converts JSON → CSV
# - Shows preview
# - Asks confirmation
# - Calculates taxes
# - Saves transactions_converted.csv
```

### Example 2: JSON with Excel Report

```bash
rye run python src/scalable_capital/main.py config.json data.json tax_report_2024.xlsx

# Output:
# - Converts JSON → CSV
# - Shows preview
# - Asks confirmation
# - Calculates taxes
# - Generates Excel report
# - Saves data_converted.csv
```

### Example 3: Canceling After Preview

```
$ rye run python src/scalable_capital/main.py config.json transactions.json

JSON FILE DETECTED
Converting...
✓ Converted 50 transactions

CSV PREVIEW...
(shows preview)

Does the CSV look correct? Continue with tax calculation? (yes/no): no

Operation cancelled by user.
Note: The converted CSV has been saved at: transactions_converted.csv
You can review it and run the tax calculator manually if needed.
```

## Troubleshooting

### JSON File Not Recognized

**Problem**: Tool treats your JSON file as CSV

**Solution**: Ensure file has `.json` extension or contains valid JSON

### Conversion Error

**Problem**: Error during JSON to CSV conversion

**Solution**:
- Verify JSON structure matches expected format
- Check that JSON is valid (use a JSON validator)
- Ensure all required fields are present

### Missing Transactions

**Problem**: Some transactions don't appear in CSV

**Solution**:
- Check the `total` field in JSON response
- API may paginate results - ensure you have all pages
- Verify transaction types are supported

### Time Differences

**Problem**: Transaction times differ from CSV export

**Solution**: This is expected - JSON uses UTC time, CSV uses local time

## Tips

1. **Save the Converted CSV**: The tool saves the converted CSV for future use
2. **Verify Before Confirming**: Always check the preview before proceeding
3. **Reuse Converted CSV**: Once converted, you can use the CSV file directly
4. **Keep Original JSON**: Keep the JSON file as backup

## Support

For issues or questions:
- Check this guide first
- Review the main README.md
- Check existing issues on GitHub
- Create a new issue with example data (redact sensitive info)
