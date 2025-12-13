# JSON Support Usage Guide

This guide explains how to use the JSON import feature to process transactions directly from the Scalable Capital API.

## Getting Your Transaction Data (JSON)

### Method 1: Browser (Simple - Recommended for Most Users)

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

### Method 2: curl (Advanced - Get More Transactions Per Request)

If you have many transactions, you can use `curl` to fetch more transactions in a single request by customizing the page size:

**Step 1: Get Your Session Cookie**
1. Log in to Scalable Capital in your browser
2. Open Developer Tools (F12 or right-click → Inspect)
3. Go to the Network tab
4. Refresh the page
5. Find any request to `scalable.capital`
6. Copy the `Cookie` header value

**Step 2: Make the API Request**
```bash
curl 'https://de.scalable.capital/broker/api/data' \
  -H 'Cookie: YOUR_SESSION_COOKIE_HERE' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "id": "transactions",
    "input": {
      "pageSize": 500,
      "type": [],
      "status": [],
      "searchTerm": "",
      "cursor": null
    }
  }' > transactions.json
```

**Customization Options:**
- `pageSize`: Number of transactions per request (default: 50, increase to 500+ for more data)
- `type`: Filter by transaction type (leave empty `[]` for all types)
- `status`: Filter by status (leave empty `[]` for all statuses)
- `searchTerm`: Search for specific ISIN or text (leave empty `""` for all)
- `cursor`: For pagination - use `null` for first page

**Example: Fetch 1000 Transactions**
```bash
curl 'https://de.scalable.capital/broker/api/data' \
  -H 'Cookie: YOUR_SESSION_COOKIE' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "id": "transactions",
    "input": {
      "pageSize": 1000,
      "type": [],
      "status": [],
      "searchTerm": "",
      "cursor": null
    }
  }' > transactions.json
```

> **Security Note**: Your session cookie is sensitive. Don't share it with anyone and delete it from your command history after use.

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
- **Smart Filtering**: Automatically excludes cash transactions and non-trade transactions - only includes buy/sell executions
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
   (Skipped 34 non-execution transactions - only buy/sell executions are included)
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

The converter **only includes SETTLED (executed) buy/sell transactions** that are relevant for tax calculations:

### Included: Executed Security Transactions
**Requirements**: Must be `SECURITY_TRANSACTION` type AND `SETTLED` status

- ✅ **Savings Plans** (recurring purchases) → `Savings plan`
- ✅ **Buy Orders** (manual purchases) → `Buy`
- ✅ **Single Orders** (one-time purchases) → `Buy`
- ✅ **Sell Orders** (executed sales) → `Sell`

### Excluded: Non-Execution Transactions

**Transaction Type: `CASH_TRANSACTION`** (all statuses)
- ❌ **Cash Deposits** (e.g., bank transfers to your account) - Skipped
- ❌ **Cash Withdrawals** (e.g., bank transfers from your account) - Skipped
- ❌ **Fees** (e.g., account maintenance fees) - Skipped
- ❌ **Interest** (e.g., interest on cash balance) - Skipped

**Transaction Type: `NON_TRADE_SECURITY_TRANSACTION`** (all statuses)
- ❌ **Security Transfers In** (e.g., depot transfers from another broker) - Skipped
- ❌ **Security Transfers Out** (e.g., depot transfers to another broker) - Skipped
- ❌ **Stock Splits** - Skipped
- ❌ **Corporate Actions** - Skipped

**Transaction Type: `SECURITY_TRANSACTION`** with non-SETTLED status
- ❌ **Cancelled Orders** (status: `CANCELED` or `CANCELLED`) - Skipped
- ❌ **Pending Orders** (status: `PENDING`) - Skipped
- ❌ **Failed Orders** (any non-SETTLED status) - Skipped

> **Note**: Only executed buy/sell transactions (type `SECURITY_TRANSACTION` AND status `SETTLED`) are included. All other transactions are automatically filtered out because they're not needed for calculating capital gains or distribution equivalent income. The tool will inform you how many transactions were skipped during conversion.

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
