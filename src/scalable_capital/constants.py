"""
Constants used throughout the Scalable Capital AT Tax Report application.

This module centralizes all magic numbers, string literals, and configuration values
to improve maintainability and reduce duplication.
"""

# Tax rates
AUSTRIAN_CAPITAL_GAINS_TAX_RATE = 0.275  # 27.5% Austrian KESt

# File encoding
DEFAULT_FILE_ENCODING = 'utf-8'

# CSV configuration
CSV_DELIMITER = ';'
CSV_DECIMAL = ','

# Decimal precision for different types of values
DECIMAL_PRECISION_QUANTITY = 3
DECIMAL_PRECISION_PRICE = 4
DECIMAL_PRECISION_CURRENCY = 2
DECIMAL_PRECISION_PERCENTAGE = 2

# Excel formatting
EXCEL_HEADER_BG_COLOR = '#4472C4'
EXCEL_HEADER_TEXT_COLOR = 'white'
EXCEL_ETF_BG_COLOR = '#E7E6E6'
EXCEL_STOCK_BG_COLOR = 'white'
EXCEL_COLUMN_WIDTH_NARROW = 12
EXCEL_COLUMN_WIDTH_MEDIUM = 15
EXCEL_COLUMN_WIDTH_WIDE = 18
EXCEL_COLUMN_WIDTH_EXTRA_WIDE = 25

# Date formats
DATE_FORMAT_DISPLAY = '%Y-%m-%d'
DATETIME_FORMAT_ISO = '%Y-%m-%dT%H:%M:%S.%fZ'

# Terminal display
TERMINAL_TABLE_WIDTH = 120
TERMINAL_SECTION_SEPARATOR = '=' * 120
TERMINAL_SUBSECTION_SEPARATOR = '-' * 120

# Transaction types mapping (for JSON conversion)
JSON_TRANSACTION_TYPE_BUY = 'security_buy'
JSON_TRANSACTION_TYPE_SELL = 'security_sell'
JSON_TRANSACTION_TYPE_PAYMENT_INBOUND = 'payment_inbound'
JSON_TRANSACTION_TYPE_PAYMENT_OUTBOUND = 'payment_outbound'

# Currency
DEFAULT_CURRENCY = 'EUR'

# ISIN validation
ISIN_LENGTH = 12

# Preview limits
CSV_PREVIEW_LINES = 50
