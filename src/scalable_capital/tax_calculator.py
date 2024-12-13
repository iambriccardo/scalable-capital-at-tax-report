"""
Tax calculator for Austrian investment funds based on OeKB reports.
Handles computation of distribution equivalent income and foreign taxes.

The calculator processes transactions for investment funds and calculates:
- Distribution equivalent income (Ausschüttungsgleiche Erträge)
- Foreign taxes paid (Anzurechnende ausländische Quellensteuer)
- Moving average prices
- Capital gains
"""
import csv
from typing import List, Tuple, Union

from currency_converter import CurrencyConverter

from scalable_capital.models import (
    Transaction, Config, BuyTransaction, AdjustmentTransaction, 
    SellTransaction, ComputedTransaction, TaxCalculationResult
)

class TaxCalculator:
    """
    Calculates Austrian taxes for investment funds based on OeKB reports.
    
    This class handles:
    - Loading and parsing transaction data
    - Computing distribution equivalent income
    - Calculating foreign taxes
    - Processing buy/sell transactions
    - Adjusting moving average prices
    """

    def __init__(self, configs: List[Config], csv_file_path: str):
        """
        Initialize the tax calculator with fund configurations and transaction data.

        Args:
            configs: List of Config objects containing fund configurations
            csv_file_path: Path to CSV file containing transaction data
        """
        self.configs = configs
        self.csv_file_path = csv_file_path
        self.transactions = self._load_transactions()

    def _load_transactions(self) -> List[Transaction]:
        """
        Load and parse transactions from the CSV file.

        Returns:
            List of Transaction objects
        """
        transactions = []
        
        with open(self.csv_file_path, 'r') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                transaction = Transaction.from_csv_row(row)
                transactions.append(transaction)

        return transactions

    @staticmethod
    def _to_ecb_rate(ecb_exchange_rate: float, value: float) -> float:
        """Convert a value using ECB exchange rate, rounded to 4 decimal places."""
        return round(ecb_exchange_rate * value, 4)

    def _compute_distribution_equivalent_income(
            self, config: Config, ecb_exchange_rate: float, quantity_at_report: float
    ) -> float:
        """
        Calculate distribution equivalent income (Ausschüttungsgleiche Erträge 27,5%).
        
        Args:
            config: Fund configuration
            ecb_exchange_rate: Exchange rate from fund currency to EUR
            quantity_at_report: Number of shares held at report date
            
        Returns:
            Distribution equivalent income in EUR
        """
        return round(
            self._to_ecb_rate(ecb_exchange_rate, config.oekb_distribution_equivalent_income_factor)
            * quantity_at_report,
            4
        )

    def _compute_taxes_paid_abroad(
            self, config: Config, ecb_exchange_rate: float, quantity_at_report: float
    ) -> float:
        """
        Calculate foreign taxes paid (Anzurechnende ausländische Quellensteuer).
        
        Args:
            config: Fund configuration
            ecb_exchange_rate: Exchange rate from fund currency to EUR
            quantity_at_report: Number of shares held at report date
            
        Returns:
            Foreign taxes paid in EUR
        """
        return round(
            self._to_ecb_rate(ecb_exchange_rate, config.oekb_taxes_paid_abroad_factor)
            * quantity_at_report,
            4
        )

    def _compute_adjustment_factor(self, config: Config, ecb_exchange_rate: float) -> float:
        """Calculate the adjustment factor for acquisition costs."""
        return round(self._to_ecb_rate(ecb_exchange_rate, config.oekb_adjustment_factor), 4)

    def _process_single_fund(self, config: Config) -> TaxCalculationResult:
        """Process tax calculations for a single fund."""
        # Filter transactions for this specific ISIN
        isin_transactions = [t for t in self.transactions if t.isin == config.isin]

        starting_total_quantity = round(config.starting_quantity, 3)
        starting_total_quantity_before_report = starting_total_quantity
        starting_moving_avg_price = round(config.starting_moving_avg_price, 4)

        # Get ECB exchange rate
        ecb_exchange_rate = round(
            CurrencyConverter().convert(1, config.oekb_report_currency, date=config.oekb_report_date),
            4
        )

        # Process transactions
        computed_transactions = self._prepare_transactions(isin_transactions, config)
        computed_transactions = self._insert_adjustment_factor(
            computed_transactions,
            config,
            ecb_exchange_rate
        )

        # Calculate moving average price
        total_quantity, total_quantity_before_report, total_capital_gains, final_moving_avg_price = self._calculate_transaction_totals(
            computed_transactions,
            config,
            starting_total_quantity,
            starting_total_quantity_before_report,
            starting_moving_avg_price
        )

        # Calculate final values
        distribution_equivalent_income, taxes_paid_abroad = self._calculate_fund_totals(
            config,
            ecb_exchange_rate,
            total_quantity_before_report
        )

        # Create result model
        return TaxCalculationResult(
            isin=config.isin,
            report_currency=config.oekb_report_currency,
            start_date=config.start_date,
            end_date=config.end_date,
            report_date=config.oekb_report_date,
            distribution_equivalent_income_factor=config.oekb_distribution_equivalent_income_factor,
            taxes_paid_abroad_factor=config.oekb_taxes_paid_abroad_factor,
            adjustment_factor=config.oekb_adjustment_factor,
            ecb_exchange_rate=ecb_exchange_rate,
            distribution_equivalent_income=distribution_equivalent_income,
            taxes_paid_abroad=taxes_paid_abroad,
            total_capital_gains=total_capital_gains,
            starting_quantity=starting_total_quantity,
            total_quantity_before_report=total_quantity_before_report,
            total_quantity=total_quantity,
            starting_moving_avg_price=starting_moving_avg_price,
            final_moving_avg_price=final_moving_avg_price,
            computed_transactions=computed_transactions
        )

    def calculate_taxes(self) -> List[TaxCalculationResult]:
        """Calculate taxes for all configured funds."""
        results = []
        for config in self.configs:
            result = self._process_single_fund(config)
            results.append(result)
        return results

    def _prepare_transactions(self, isin_transactions: List[Transaction], config: Config) -> List[ComputedTransaction]:
        """Prepare and validate transactions for processing."""
        computed_transactions = []
        for transaction in isin_transactions:
            if transaction.type.excluded():
                print(f"\n[ERROR]: Skipping transaction with type = {transaction.type.value}, status={transaction.status}")
                continue

            if config.start_date <= transaction.date <= config.end_date:
                if transaction.type.is_buy():
                    computed_transactions.append(BuyTransaction.from_transaction(transaction))
                elif transaction.type.is_sell():
                    computed_transactions.append(SellTransaction.from_transaction(transaction))

        return sorted(computed_transactions, key=lambda t: t.date)

    def _insert_adjustment_factor(self, computed_transactions: List[ComputedTransaction], config: Config,
                                  ecb_exchange_rate: float) -> List[ComputedTransaction]:
        """Insert the adjustment factor at the appropriate position in the transaction list."""
        insertion_index = 0
        for index, value in enumerate(computed_transactions):
            if config.oekb_report_date >= value.date:
                insertion_index = index + 1

        computed_transactions.insert(
            insertion_index,
            AdjustmentTransaction(
                date=config.oekb_report_date,
                adjustment_factor=self._compute_adjustment_factor(config, ecb_exchange_rate)
            )
        )

        return computed_transactions

    def _handle_adjustment_transaction(
        self, 
        transaction: AdjustmentTransaction, 
        total_quantity: float,
        moving_avg_price: float
    ) -> Tuple[float, float]:
        """
        Process an adjustment transaction and update the moving average price.

        Args:
            transaction: The adjustment transaction to process
            total_quantity: Current total quantity
            moving_avg_price: Current moving average price

        Returns:
            Tuple of (total_quantity, new_moving_avg_price)
        """
        if total_quantity != 0.0:
            new_moving_avg_price = moving_avg_price + transaction.adjustment_factor
            transaction.moving_avg_price = new_moving_avg_price
            transaction.total_quantity = total_quantity
            return total_quantity, new_moving_avg_price

        return total_quantity, moving_avg_price

    def _handle_buy_transaction(
        self,
        transaction: BuyTransaction,
        total_quantity: float,
        total_quantity_before_report: float,
        moving_avg_price: float,
        report_date: str
    ) -> Tuple[float, float, float]:
        """
        Process a buy transaction and update quantities and moving average price.

        Args:
            transaction: The buy transaction to process
            total_quantity: Current total quantity
            total_quantity_before_report: Quantity before report date
            moving_avg_price: Current moving average price
            report_date: The OeKB report date

        Returns:
            Tuple of (new_total_quantity, new_total_quantity_before_report, new_moving_avg_price)
        """
        new_moving_avg_price = round(
            ((total_quantity * moving_avg_price) + (transaction.quantity * transaction.share_price)) /
            (total_quantity + transaction.quantity),
            4
        )
        transaction.moving_avg_price = new_moving_avg_price

        new_total_quantity = round(total_quantity + transaction.quantity, 3)
        transaction.total_quantity = new_total_quantity
        new_total_quantity_before_report = total_quantity_before_report

        if transaction.date <= report_date:
            new_total_quantity_before_report = round(total_quantity_before_report + transaction.quantity, 3)

        return new_total_quantity, new_total_quantity_before_report, new_moving_avg_price

    def _handle_sell_transaction(
        self,
        transaction: SellTransaction,
        total_quantity: float,
        total_quantity_before_report: float,
        report_date: str
    ) -> Tuple[float, float]:
        """
        Process a sell transaction and update quantities.

        Args:
            transaction: The sell transaction to process
            total_quantity: Current total quantity
            total_quantity_before_report: Quantity before report date
            report_date: The OeKB report date

        Returns:
            Tuple of (new_total_quantity, new_total_quantity_before_report)
        """
        new_total_quantity = round(total_quantity - transaction.quantity, 3)
        transaction.total_quantity = new_total_quantity
        new_total_quantity_before_report = total_quantity_before_report

        if transaction.date <= report_date:
            new_total_quantity_before_report = round(total_quantity_before_report - transaction.quantity, 3)

        return new_total_quantity, new_total_quantity_before_report

    def _calculate_transaction_totals(
        self,
        computed_transactions: List[ComputedTransaction],
        config: Config,
        starting_total_quantity: float,
        starting_total_quantity_before_report: float,
        starting_moving_avg_price: float
    ) -> Tuple[float, float, float, float]:
        """
        Calculate transaction totals and moving average price.

        Args:
            computed_transactions: List of transactions to process
            config: Fund configuration
            starting_total_quantity: Initial total quantity
            starting_total_quantity_before_report: Initial quantity before report
            starting_moving_avg_price: Initial moving average price

        Returns:
            Tuple of (total_quantity, total_quantity_before_report, total_capital_gains, final_moving_avg_price)
        """
        total_quantity = starting_total_quantity
        total_quantity_before_report = starting_total_quantity_before_report
        total_capital_gains = 0.0
        moving_avg_price = starting_moving_avg_price

        for transaction in computed_transactions:
            if isinstance(transaction, AdjustmentTransaction):
                total_quantity, moving_avg_price = self._handle_adjustment_transaction(
                    transaction, total_quantity, moving_avg_price
                )
            elif isinstance(transaction, BuyTransaction):
                total_quantity, total_quantity_before_report, moving_avg_price = self._handle_buy_transaction(
                    transaction, total_quantity, total_quantity_before_report,
                    moving_avg_price, config.oekb_report_date
                )
            elif isinstance(transaction, SellTransaction):
                total_quantity, total_quantity_before_report = self._handle_sell_transaction(
                    transaction, total_quantity, total_quantity_before_report, config.oekb_report_date
                )

        return total_quantity, total_quantity_before_report, total_capital_gains, moving_avg_price

    def _calculate_fund_totals(self, config: Config, ecb_exchange_rate: float,
                               total_quantity_before_report: float) -> Tuple[float, float]:
        """Calculate the final totals for a fund."""
        distribution_equivalent_income = self._compute_distribution_equivalent_income(
            config, ecb_exchange_rate, total_quantity_before_report)
        taxes_paid_abroad = self._compute_taxes_paid_abroad(
            config, ecb_exchange_rate, total_quantity_before_report)

        return distribution_equivalent_income, taxes_paid_abroad
