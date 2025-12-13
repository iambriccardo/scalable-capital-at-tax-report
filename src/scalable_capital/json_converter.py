"""
JSON to CSV converter for Scalable Capital transaction data.
Converts API JSON responses to CSV format compatible with the tax calculator.
"""
import json
import csv
from datetime import datetime
from typing import List, Dict, Any


def parse_datetime(iso_datetime: str) -> tuple[str, str]:
    """
    Parse ISO datetime string and return date and time separately.

    Args:
        iso_datetime: ISO format datetime string (e.g., "2025-03-10T10:33:23.220Z")

    Returns:
        Tuple of (date_str, time_str) in format (YYYY-MM-DD, HH:MM:SS)
    """
    dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M:%S')


def map_security_transaction_type(sec_type: str) -> str:
    """
    Map JSON security transaction type to CSV type.

    Args:
        sec_type: Security transaction type from JSON

    Returns:
        Mapped type for CSV
    """
    mapping = {
        'SAVINGS_PLAN': 'Savings plan',
        'BUY': 'Buy',
        'SINGLE': 'Buy',  # Single buy order (one-time purchase)
        'SELL': 'Sell'
    }
    return mapping.get(sec_type, sec_type)


def map_cash_transaction_type(cash_type: str) -> str:
    """
    Map JSON cash transaction type to CSV type.

    Args:
        cash_type: Cash transaction type from JSON

    Returns:
        Mapped type for CSV
    """
    mapping = {
        'DEPOSIT': 'Deposit',
        'WITHDRAWAL': 'Withdrawal',
        'FEE': 'Fee',
        'INTEREST': 'Interest'
    }
    return mapping.get(cash_type, cash_type)


def map_status(status: str) -> str:
    """
    Map JSON status to CSV status.

    Args:
        status: Status from JSON

    Returns:
        Mapped status for CSV
    """
    mapping = {
        'SETTLED': 'Executed',
        'CANCELED': 'Cancelled',
        'CANCELLED': 'Cancelled'
    }
    return mapping.get(status, status)


def format_decimal(value: float, precision: int = None) -> str:
    """
    Format a number to European decimal format (comma as decimal separator).

    Args:
        value: Number to format
        precision: Number of decimal places (None = automatic)

    Returns:
        Formatted string with comma as decimal separator
    """
    if value is None:
        return ''

    if precision is None:
        # Use automatic precision, removing unnecessary trailing zeros
        formatted = f'{value:.10f}'.rstrip('0').rstrip('.')
    else:
        formatted = f'{value:.{precision}f}'

    # Replace dot with comma for European format
    return formatted.replace('.', ',')


def convert_security_transaction(tx: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert a security transaction from JSON to CSV row format.

    Args:
        tx: Transaction dictionary from JSON

    Returns:
        Dictionary with CSV column names as keys
    """
    date, time = parse_datetime(tx['lastEventDateTime'])

    # Calculate price per share: amount / quantity
    quantity = tx['quantity']
    amount = tx['amount']
    price = abs(amount / quantity) if quantity != 0 else 0

    # Determine if it's a buy or sell based on side
    side = tx.get('side', 'BUY')
    if side == 'SELL':
        csv_type = 'Sell'
    else:
        csv_type = map_security_transaction_type(tx['securityTransactionType'])

    return {
        'date': date,
        'time': time,
        'status': map_status(tx['status']),
        'reference': tx['id'],
        'description': tx['description'],
        'assetType': 'Security',
        'type': csv_type,
        'isin': tx['isin'],
        'shares': format_decimal(quantity),
        'price': format_decimal(price, precision=2),
        'amount': format_decimal(amount),
        'fee': '0,00',
        'tax': '0,00',
        'currency': tx['currency']
    }


def convert_cash_transaction(tx: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert a cash transaction from JSON to CSV row format.

    Args:
        tx: Transaction dictionary from JSON

    Returns:
        Dictionary with CSV column names as keys
    """
    date, time = parse_datetime(tx['lastEventDateTime'])

    return {
        'date': date,
        'time': time,
        'status': map_status(tx['status']),
        'reference': tx['id'],
        'description': tx['description'],
        'assetType': 'Cash',
        'type': map_cash_transaction_type(tx['cashTransactionType']),
        'isin': tx.get('relatedIsin', '') or '',
        'shares': '',
        'price': '',
        'amount': format_decimal(tx['amount']),
        'fee': '0,00',
        'tax': '0,00',
        'currency': tx['currency']
    }


def convert_non_trade_security_transaction(tx: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert a non-trade security transaction from JSON to CSV row format.

    Args:
        tx: Transaction dictionary from JSON

    Returns:
        Dictionary with CSV column names as keys
    """
    date, time = parse_datetime(tx['lastEventDateTime'])

    # Calculate price per share
    quantity = tx['quantity']
    amount = tx['amount']
    price = abs(amount / quantity) if quantity != 0 else 0

    # Map non-trade transaction type to something meaningful
    # For now, treating TRANSFER_IN as Buy and TRANSFER_OUT as Sell
    non_trade_type = tx['nonTradeSecurityTransactionType']
    if non_trade_type == 'TRANSFER_IN':
        csv_type = 'Buy'
    elif non_trade_type == 'TRANSFER_OUT':
        csv_type = 'Sell'
    else:
        csv_type = non_trade_type

    return {
        'date': date,
        'time': time,
        'status': map_status(tx['status']),
        'reference': tx['id'],
        'description': tx['description'],
        'assetType': 'Security',
        'type': csv_type,
        'isin': tx['isin'],
        'shares': format_decimal(abs(quantity)),
        'price': format_decimal(price, precision=2),
        'amount': format_decimal(amount),
        'fee': '0,00',
        'tax': '0,00',
        'currency': tx['currency']
    }


def convert_json_to_csv(json_file_path: str, csv_output_path: str) -> int:
    """
    Convert Scalable Capital JSON transaction data to CSV format.

    Only includes SETTLED (executed) security transactions (buy/sell/savings plans).
    Excludes:
    - Cash transactions (deposits, withdrawals, fees, interest)
    - Non-trade security transactions (transfers, splits, corporate actions)
    - Non-executed security transactions (cancelled, pending orders)

    Args:
        json_file_path: Path to input JSON file
        csv_output_path: Path for output CSV file

    Returns:
        Number of transactions converted
    """
    # Load JSON data
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # Extract transactions from nested structure
    transactions = data[0]['data']['account']['brokerPortfolio']['moreTransactions']['transactions']

    # Convert each transaction based on its type
    csv_rows = []
    skipped_count = 0

    for tx in transactions:
        tx_type = tx['type']
        tx_status = tx.get('status', '')

        # Only process SECURITY_TRANSACTION types that are SETTLED (executed)
        if tx_type == 'SECURITY_TRANSACTION' and tx_status == 'SETTLED':
            csv_row = convert_security_transaction(tx)
            csv_rows.append(csv_row)
        elif tx_type == 'SECURITY_TRANSACTION' and tx_status != 'SETTLED':
            # Skip non-executed security transactions (cancelled, pending, etc.)
            skipped_count += 1
            continue
        elif tx_type == 'NON_TRADE_SECURITY_TRANSACTION':
            # Skip non-trade security transactions (transfers, etc.)
            skipped_count += 1
            continue
        elif tx_type == 'CASH_TRANSACTION':
            # Skip cash transactions (deposits, withdrawals, fees, interest)
            skipped_count += 1
            continue
        else:
            print(f"Warning: Unknown transaction type: {tx_type}")
            skipped_count += 1
            continue

    # Sort by date and time (descending, newest first, to match original CSV)
    csv_rows.sort(key=lambda x: (x['date'], x['time']), reverse=True)

    # Write to CSV
    fieldnames = ['date', 'time', 'status', 'reference', 'description', 'assetType',
                  'type', 'isin', 'shares', 'price', 'amount', 'fee', 'tax', 'currency']

    with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(csv_rows)

    # Print summary
    if skipped_count > 0:
        print(f"  (Skipped {skipped_count} non-execution transactions - only buy/sell executions are included)")

    return len(csv_rows)
