from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Union


class TransactionType(str, Enum):
    WITHDRAWAL = "Withdrawal"
    SAVINGS_PLAN = "Savings Plan"
    DEPOSIT = "Deposit"
    FEE = "Fee"
    SELL = "Sell"
    BUY = "Buy"
    INTEREST = "Interest"

    @classmethod
    def _missing_(cls, value: str) -> 'TransactionType':
        for member in cls:
            if member.value.lower() == value.lower():
                return member

        print(f"Unknown transaction type: {value}")

        return None

    def is_buy(self) -> bool:
        return self in [TransactionType.BUY, TransactionType.SAVINGS_PLAN]
    
    def is_sell(self) -> bool:
        return self == TransactionType.SELL

    def excluded(self) -> bool:
        return self in [
            TransactionType.WITHDRAWAL,
            TransactionType.FEE,
            TransactionType.DEPOSIT,
            TransactionType.INTEREST,
        ]


@dataclass
class Transaction:
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
    # Start date of the period under consideration
    start_date: datetime
    # End date of the period under consideration
    end_date: datetime
    # Date of the OEKB report
    oekb_report_date: datetime
    # Auschüttungsgleiche Erträge 27,5% (Kennzahlen 936 oder 937)
    oekb_distribution_equivalent_income_factor: float
    # Anzurechnende ausländische (Quellen)Steuer auf Einkünfte,
    # die dem besonderen Steuersatz von 27,5% unterliegen (Kennzahl 984 oder 998)
    oekb_taxes_paid_abroad_factor: float
    # Die Anschaffungskosten des Fondsanteils sind zu korrigieren um
    oekb_adjustment_factor: float
    # OEKB report currency
    oekb_report_currency: str
    # Starting quantity of the report of the previous year
    starting_quantity: float
    # Starting moving average price of the report of the previous year
    starting_moving_avg_price: float
    # ISIN of the fund
    isin: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create a Config instance from a dictionary."""
        return cls(
            start_date=datetime.strptime(data['start_date'], '%d/%m/%Y'),
            end_date=datetime.strptime(data['end_date'], '%d/%m/%Y'),
            oekb_report_date=datetime.strptime(data['oekb_report_date'], '%d/%m/%Y'),
            oekb_distribution_equivalent_income_factor=float(data['oekb_distribution_equivalent_income_factor']),
            oekb_taxes_paid_abroad_factor=float(data['oekb_taxes_paid_abroad_factor']),
            oekb_adjustment_factor=float(data['oekb_adjustment_factor']),
            oekb_report_currency=data['oekb_report_currency'],
            starting_quantity=float(data['starting_quantity']),
            starting_moving_avg_price=float(data['starting_moving_avg_price']),
            isin=data['isin']
        )

@dataclass
class BuyTransaction:
    """Represents a buy transaction."""

    def __init__(self, date: datetime, quantity: float, share_price: float):
        self.date = date
        self.quantity = quantity
        self.share_price = share_price
        self.moving_avg_price: float = 0.0

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
class SellTransaction:
    """Represents a sell transaction."""
    
    def __init__(self, date: datetime, quantity: float, share_price: float):
        self.date = date
        self.quantity = quantity
        self.share_price = share_price
        self.moving_avg_price: float = 0.0

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
class AdjustmentTransaction:
    """Represents an adjustment transaction."""
    
    def __init__(self, date: datetime, adjustment_factor: float):
        self.date = date
        self.adjustment_factor = adjustment_factor
        self.moving_avg_price = 0.0
    
    def type_name(self) -> str:
        return "ADJ"

ComputedTransaction = Union[BuyTransaction, SellTransaction, AdjustmentTransaction]

@dataclass
class TaxCalculationResult:
    """Represents the complete tax calculation result for a single fund."""
    # Fund identification
    isin: str
    report_currency: str
    
    # Report dates
    start_date: datetime
    end_date: datetime 
    report_date: datetime
    
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