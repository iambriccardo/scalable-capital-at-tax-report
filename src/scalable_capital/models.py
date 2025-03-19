from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List


class TransactionType(str, Enum):
    """
    Enumeration of possible transaction types in the system.
    
    Inherits from both str and Enum to allow string comparison while maintaining enum functionality.
    """
    WITHDRAWAL = "Withdrawal"
    SAVINGS_PLAN = "Savings Plan"
    DEPOSIT = "Deposit"
    FEE = "Fee"
    SELL = "Sell"
    BUY = "Buy"
    INTEREST = "Interest"

    @classmethod
    def _missing_(cls, value: str) -> 'TransactionType':
        """
        Handle case-insensitive lookup of enum values.
        
        Args:
            value: String value to look up
            
        Returns:
            Matching TransactionType or None if no match found
        """
        for member in cls:
            if member.value.lower() == value.lower():
                return member

        print(f"Unknown transaction type: {value}")

        return None

    def is_buy(self) -> bool:
        """Check if transaction type represents a buy operation (including savings plans)."""
        return self in [TransactionType.BUY, TransactionType.SAVINGS_PLAN]

    def is_sell(self) -> bool:
        """Check if transaction type represents a sell operation."""
        return self == TransactionType.SELL

    def excluded(self) -> bool:
        """Check if transaction type should be excluded from calculations."""
        return self in [
            TransactionType.WITHDRAWAL,
            TransactionType.FEE,
            TransactionType.DEPOSIT,
            TransactionType.INTEREST,
        ]


class SecurityType(str, Enum):
    """Type of security being processed."""
    ACCUMULATING_ETF = "accumulating_etf"
    STOCK = "stock"

    @classmethod
    def _missing_(cls, value: str) -> 'SecurityType':
        """Handle case-insensitive lookup of enum values."""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        print(f"Unknown security type: {value}")
        return None


@dataclass
class Transaction:
    """
    Represents a single financial transaction with all its details.
    """
    type: TransactionType
    date: datetime
    time: str
    status: str
    reference: str
    description: str
    asset_type: str
    isin: str | None
    shares: Decimal
    price: Decimal
    amount: Decimal
    fee: Decimal
    tax: Decimal
    currency: str

    @classmethod
    def from_csv_row(cls, row: dict) -> 'Transaction':
        """
        Create a Transaction instance from a CSV row dictionary.
        
        Handles parsing of dates and decimal numbers in European format.
        
        Args:
            row: Dictionary containing transaction data from CSV
            
        Returns:
            New Transaction instance
        """
        # Parse date combining date and time fields
        date_str = f"{row['date']} {row['time']}"
        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        def parse_decimal(value: str) -> Decimal:
            if not value:
                return Decimal('0')
            # Convert European number format (1.234,56) to standard decimal (1234.56)
            return Decimal(value.replace('.', '').replace(',', '.'))

        return cls(
            date=date,
            time=row['time'],
            status=row['status'],
            reference=row['reference'],
            description=row['description'],
            asset_type=row['assetType'],
            type=TransactionType(row['type']),
            isin=row['isin'] or None,
            shares=parse_decimal(row['shares']),
            price=parse_decimal(row['price']),
            amount=parse_decimal(row['amount']),
            fee=parse_decimal(row.get('fee', '0')),
            tax=parse_decimal(row.get('tax', '0')),
            currency=row['currency']
        )


@dataclass
class Config:
    """
    Configuration for tax calculations of a specific security.
    
    Contains all necessary parameters for calculating taxes according to
    Austrian tax law and OeKB (Oesterreichische Kontrollbank) requirements.
    """
    # Security type
    security_type: SecurityType
    # Start date of the period under consideration
    start_date: datetime
    # End date of the period under consideration
    end_date: datetime
    # Date of the OEKB report
    oekb_report_date: datetime | None
    # Auschüttungsgleiche Erträge 27,5% (Kennzahlen 936 oder 937)
    oekb_distribution_equivalent_income_factor: float
    # Anzurechnende ausländische (Quellen)Steuer auf Einkünfte,
    # die dem besonderen Steuersatz von 27,5% unterliegen (Kennzahl 984 oder 998)
    oekb_taxes_paid_abroad_factor: float
    # Die Anschaffungskosten des Fondsanteils sind zu korrigieren um
    oekb_adjustment_factor: float
    # OEKB report currency
    oekb_report_currency: str | None
    # Starting quantity of the report of the previous year
    starting_quantity: float
    # Starting moving average price of the report of the previous year
    starting_moving_avg_price: float
    # ISIN of the fund
    isin: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create a Config instance from a dictionary."""
        security_type = SecurityType(data['type'])

        # For stocks, OEKB fields are optional and default to None/0.
        if security_type == SecurityType.STOCK:
            return cls(
                security_type=security_type,
                start_date=datetime.strptime(data['start_date'], '%d/%m/%Y'),
                end_date=datetime.strptime(data['end_date'], '%d/%m/%Y'),
                oekb_report_date=None,
                oekb_distribution_equivalent_income_factor=0.0,
                oekb_taxes_paid_abroad_factor=0.0,
                oekb_adjustment_factor=0.0,
                oekb_report_currency=None,
                starting_quantity=float(data['starting_quantity']),
                starting_moving_avg_price=float(data['starting_moving_avg_price']),
                isin=data['isin']
            )

        # We check if the ETF has a report date, otherwise we just default it to None, meaning no OEKB related
        # data will be computed.
        if (oekb_report_date := data.get('oekb_report_date')) is not None:
            oekb_report_date = datetime.strptime(oekb_report_date, '%d/%m/%Y')
        else:
            oekb_report_date = None

        return cls(
            security_type=security_type,
            start_date=datetime.strptime(data['start_date'], '%d/%m/%Y'),
            end_date=datetime.strptime(data['end_date'], '%d/%m/%Y'),
            oekb_report_date=oekb_report_date,
            oekb_distribution_equivalent_income_factor=float(data.get('oekb_distribution_equivalent_income_factor', 0.0)),
            oekb_taxes_paid_abroad_factor=float(data.get('oekb_taxes_paid_abroad_factor', 0.0)),
            oekb_adjustment_factor=float(data.get('oekb_adjustment_factor', 0.0)),
            oekb_report_currency=data.get('oekb_report_currency'),
            starting_quantity=float(data['starting_quantity']),
            starting_moving_avg_price=float(data['starting_moving_avg_price']),
            isin=data['isin']
        )


@dataclass
class ComputedTransaction:
    """
    Base class for all computed transactions in the tax calculation process.
    
    Provides common functionality and interface for different types of
    computed transactions (buy, sell, adjustment).
    """

    def __init__(self, date: datetime):
        self.date = date
        self.total_quantity = 0.0
        self.moving_avg_price = 0.0

    def total_price(self) -> float:
        """Calculate total price of transaction. Override in subclasses."""
        raise NotImplementedError

    def type_name(self) -> str:
        """Return transaction type name. Override in subclasses."""
        raise NotImplementedError


@dataclass
class BuyTransaction(ComputedTransaction):
    """
    Represents a computed buy transaction.
    """
    quantity: float
    share_price: float

    def __init__(self, date: datetime, quantity: float, share_price: float):
        super().__init__(date)
        self.quantity = quantity
        self.share_price = share_price

    @classmethod
    def from_transaction(cls, transaction: Transaction) -> 'BuyTransaction':
        """Create a BuyTransaction from a Transaction."""
        return cls(
            date=transaction.date,
            quantity=float(transaction.shares),
            share_price=float(transaction.price)
        )

    def total_price(self) -> float:
        return round(self.quantity * self.share_price, 4)

    def type_name(self) -> str:
        return "BUY"


@dataclass
class SellTransaction(ComputedTransaction):
    """
    Represents a computed sell transaction.
    """
    quantity: float
    share_price: float

    def __init__(self, date: datetime, quantity: float, share_price: float):
        super().__init__(date)
        self.quantity = quantity
        self.share_price = share_price

    @classmethod
    def from_transaction(cls, transaction: Transaction) -> 'SellTransaction':
        """Create a SellTransaction from a Transaction."""
        return cls(
            date=transaction.date,
            quantity=float(transaction.shares),
            share_price=float(transaction.price)
        )

    def total_price(self) -> float:
        return round(self.quantity * self.share_price, 4)

    def type_name(self) -> str:
        return "SELL"


@dataclass
class AdjustmentTransaction(ComputedTransaction):
    """
    Represents an adjustment to the moving average price.
    
    Used when OeKB adjustment factors need to be applied.
    """
    adjustment_factor: float

    def __init__(self, date: datetime, adjustment_factor: float):
        super().__init__(date)
        self.adjustment_factor = adjustment_factor

    def type_name(self) -> str:
        return "ADJ"

    def total_price(self) -> float:
        return 0.0


@dataclass
class TaxCalculationResult:
    """
    Complete tax calculation result for a single fund.
    
    Contains all input parameters, intermediate calculations,
    and final results needed for tax reporting.
    """
    # Fund identification
    isin: str
    report_currency: str
    security_type: SecurityType

    # Report dates
    start_date: datetime
    end_date: datetime
    report_date: datetime | None

    # OeKB factors
    distribution_equivalent_income_factor: float
    taxes_paid_abroad_factor: float
    adjustment_factor: float

    # ECB exchange rate
    ecb_exchange_rate: float

    # Computed values from OeKB factors
    distribution_equivalent_income: float
    taxes_paid_abroad: float

    # Total capital gains
    total_capital_gains: float

    # Quantity tracking
    starting_quantity: float
    total_quantity_before_report: float
    total_quantity: float

    # Price tracking 
    starting_moving_avg_price: float
    final_moving_avg_price: float

    # Transaction history
    computed_transactions: List[ComputedTransaction]
