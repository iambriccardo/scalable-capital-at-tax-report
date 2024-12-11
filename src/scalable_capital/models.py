from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Optional


class TransactionType(str, Enum):
    WITHDRAWAL = "Withdrawal"
    SAVINGS_PLAN = "Savings plan"
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

    def excluded(self) -> bool:
        return self in [
            TransactionType.WITHDRAWAL,
            TransactionType.FEE,
            TransactionType.DEPOSIT,
            TransactionType.INTEREST,
            # TODO: add support for SELL later.
            TransactionType.SELL
        ]


@dataclass
class Transaction:
    date: datetime
    time: str
    status: str
    reference: str
    description: str
    asset_type: str
    type: TransactionType
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
class ComputedTransaction:
    """Represents a processed transaction with computed values."""
    date: datetime
    quantity: float
    share_price: float
    total_price: float

    @classmethod
    def from_transaction(cls, transaction: 'Transaction') -> 'ComputedTransaction':
        """Create a ComputedTransaction from a Transaction."""
        quantity = float(transaction.shares)
        total_price = abs(float(transaction.amount))
        share_price = round(total_price / quantity, 4)
        
        return cls(
            date=transaction.date,
            quantity=quantity,
            share_price=share_price,
            total_price=total_price
        )
