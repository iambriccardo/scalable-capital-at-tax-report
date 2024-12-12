"""
Tax calculator for Austrian investment funds based on OeKB reports.
Handles computation of distribution equivalent income and foreign taxes.
"""
import csv
from typing import List, Tuple, Union

from currency_converter import CurrencyConverter

from scalable_capital.models import Transaction, Config, ComputedTransaction, TaxCalculationResult


class TaxCalculator:
    """Calculates Austrian taxes for investment funds based on OeKB reports."""

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
        """
        Process tax calculations for a single fund.

        Args:
            config: Fund configuration

        Returns:
            TaxCalculationResult containing all computed values
        """
        # Filter transactions for this specific ISIN
        isin_transactions = [t for t in self.transactions if t.isin == config.isin]

        total_quantity = round(config.starting_quantity, 3)
        total_quantity_before_report = total_quantity
        starting_moving_avg_price = round(config.starting_moving_avg_price, 4)

        # Get ECB exchange rate
        ecb_exchange_rate = round(
            CurrencyConverter().convert(1, config.oekb_report_currency, date=config.oekb_report_date),
            4
        )

        # Print initial details
        self._print_fund_details(config, ecb_exchange_rate)

        # Process transactions
        computed_transactions = self._prepare_transactions(isin_transactions, config)
        computed_transactions = self._insert_adjustment_factor(
            computed_transactions,
            config,
            ecb_exchange_rate
        )

        # Calculate moving average price
        total_quantity, total_quantity_before_report, final_moving_avg_price = self._calculate_transaction_totals(
            computed_transactions,
            config,
            total_quantity,
            total_quantity_before_report,
            starting_moving_avg_price
        )

        # Print transactions
        self._print_transactions(config, computed_transactions, total_quantity)

        # Calculate final values
        distribution_equivalent_income, taxes_paid_abroad = self._calculate_fund_totals(
            config,
            ecb_exchange_rate,
            total_quantity_before_report
        )

        # Print capital gains and stats
        self._print_capital_gains(distribution_equivalent_income, taxes_paid_abroad)
        self._print_stats(config, total_quantity_before_report, total_quantity)

        # Create result model
        return TaxCalculationResult(
            isin=config.isin,
            report_date=config.oekb_report_date,
            start_date=config.start_date,
            end_date=config.end_date,
            distribution_equivalent_income_factor=config.oekb_distribution_equivalent_income_factor,
            taxes_paid_abroad_factor=config.oekb_taxes_paid_abroad_factor,
            adjustment_factor=config.oekb_adjustment_factor,
            report_currency=config.oekb_report_currency,
            ecb_exchange_rate=ecb_exchange_rate,
            distribution_equivalent_income=distribution_equivalent_income,
            taxes_paid_abroad=taxes_paid_abroad,
            starting_quantity=config.starting_quantity,
            quantity_at_report=total_quantity_before_report,
            final_quantity=total_quantity,
            starting_moving_avg_price=starting_moving_avg_price,
            final_moving_avg_price=final_moving_avg_price,
            computed_transactions=computed_transactions
        )

    def calculate_taxes(self) -> List[TaxCalculationResult]:
        """
        Calculate taxes for all configured funds.

        Returns:
            List of TaxCalculationResult objects, one per fund
        """
        results = []
        total_distribution_equivalent_income = 0
        total_taxes_paid_abroad = 0

        for config in self.configs:
            result = self._process_single_fund(config)
            results.append(result)

            total_distribution_equivalent_income += result.distribution_equivalent_income
            total_taxes_paid_abroad += result.taxes_paid_abroad

        self._print_final_summary(total_distribution_equivalent_income, total_taxes_paid_abroad)

        return results

    def _print_fund_details(self, config: Config, ecb_exchange_rate: float) -> None:
        """Print the details of a fund including OeKB factors and exchange rate."""
        print("\n" + "=" * 80)
        print(f"{'DETAILS':^80}")
        print("=" * 80 + "\n")

        print(f"Config ISIN: {config.isin}")
        print(f"Data file: {self.csv_file_path}\n")

        print("OeKB Factors:")
        print(f"  • Distribution equivalent income: {config.oekb_distribution_equivalent_income_factor:.4f}")
        print(f"  • Taxes paid abroad: {config.oekb_taxes_paid_abroad_factor:.4f}")
        print(f"  • Adjustment: {config.oekb_adjustment_factor:.4f}\n")

        print(
            f"Exchange rate ({config.oekb_report_currency} → EUR) at {config.oekb_report_date.strftime('%d/%m/%Y')}: {ecb_exchange_rate:.4f}")

    def _print_transactions(self, config: Config, computed_transactions: List[Union[ComputedTransaction, float]],
                            total_quantity: float) -> None:
        """Print the transaction details including headers and computed values."""
        print("\n" + "=" * 80)
        print(f"{'TRANSACTIONS':^80}")
        print("=" * 80 + "\n")

        # Print header with proper spacing
        print(f"{'Date':12} {'Quantity':>10} {'Share Price':>12} {'Total Price':>12} {'Moving Avg':>12}")
        print("-" * 62)

        # Print starting quantity and starting moving average price
        print(
            f"{config.start_date.strftime('%d/%m/%Y'):12} {config.starting_quantity:>10.3f} {'N/A':>12} {'N/A':>12} {config.starting_moving_avg_price:>12.4f}")

        # Print all transactions
        for value in computed_transactions:
            if isinstance(value, float) and total_quantity != 0.0:
                print(
                    f"{config.oekb_report_date.strftime('%d/%m/%Y')}        Adjustment of moving avg: {value:+.4f}")
            elif isinstance(value, ComputedTransaction):
                print(
                    f"{value.date.strftime('%d/%m/%Y'):12} {value.quantity:>10.3f} {value.share_price:>12.3f} "
                    f"{value.total_price:>12.4f} {value.moving_avg_price:>12.4f}")

    def _print_capital_gains(self, distribution_equivalent_income: float, taxes_paid_abroad: float) -> None:
        """Print the capital gains information."""
        print("\n" + "=" * 80)
        print(f"{'CAPITAL GAINS':^80}")
        print("=" * 80 + "\n")

        # We have to round to 2 decimals since this is what Finanzonline expects
        dei = round(distribution_equivalent_income, 2)
        tpa = round(taxes_paid_abroad, 2)

        print(f"{'Distribution equivalent income (936/937):':<50} {dei:>10.2f} EUR")
        print(f"{'Taxes paid abroad (984/998):':<50} {tpa:>10.2f} EUR")

    def _print_stats(self, config: Config, total_quantity_before_report: float, total_quantity: float) -> None:
        """Print statistics about share quantities."""
        print("\n" + "=" * 80)
        print(f"{'STATS':^80}")
        print("=" * 80 + "\n")

        print(
            f"Total shares before OeKB report ({config.oekb_report_date.strftime('%d/%m/%Y')}): {total_quantity_before_report:,.3f}")
        print(f"Current total shares:                         {total_quantity:,.3f}")

    def _print_final_summary(self, total_distribution_equivalent_income: float, total_taxes_paid_abroad: float) -> None:
        """Print the final summary of all calculations."""
        print("\n" + "=" * 80)
        print(f"{'FINAL SUMMARY (ALL FUNDS)':^80}")
        print("=" * 80 + "\n")

        # We have to round to 2 decimals since this is what Finanzonline expects
        dei = round(total_distribution_equivalent_income, 2)
        tpa = round(total_taxes_paid_abroad, 2)
        projected = round((total_distribution_equivalent_income * 0.275) - total_taxes_paid_abroad, 2)

        print(f"{'Distribution equivalent income (936/937):':<50} {dei:>10.2f} EUR")
        print(f"{'Taxes paid abroad (984/998):':<50} {tpa:>10.2f} EUR")
        print(f"\n{'Projected taxes to pay:':<50} {projected:>10.2f} EUR")
        print("\nNote: All amounts are rounded to 2 decimal places as required by Finanzonline.")

    def _prepare_transactions(self, isin_transactions: List[Transaction], config: Config) -> List[
        Union[ComputedTransaction, float]]:
        """Prepare and validate transactions for processing."""
        computed_transactions = []
        for transaction in isin_transactions:
            if not transaction.type.is_buy() and not transaction.type.excluded():
                print(
                    f"\n[ERROR]: Skipping transaction with type = {transaction.type.value}, status={transaction.status}")
                continue

            if config.start_date <= transaction.date <= config.end_date:
                computed_transactions.append(ComputedTransaction.from_transaction(transaction))

        return sorted(computed_transactions, key=lambda t: t.date)

    def _insert_adjustment_factor(self, computed_transactions: List[Union[ComputedTransaction, float]], config: Config,
                                  ecb_exchange_rate: float) -> List[Union[ComputedTransaction, float]]:
        """Insert the adjustment factor at the appropriate position in the transaction list."""
        insertion_index = 0
        for index, value in enumerate(computed_transactions):
            if config.oekb_report_date >= value.date:
                insertion_index = index + 1

        computed_transactions.insert(
            insertion_index,
            self._compute_adjustment_factor(config, ecb_exchange_rate)
        )
        return computed_transactions

    def _calculate_transaction_totals(self, computed_transactions: List[Union[ComputedTransaction, float]],
                                      config: Config,
                                      total_quantity: float, total_quantity_before_report: float,
                                      starting_moving_avg_price: float) -> Tuple[float, float, float]:
        """Calculate transaction totals and moving average price."""
        moving_avg_price = starting_moving_avg_price

        for value in computed_transactions:
            # Adjustment factor
            if isinstance(value, float) and total_quantity != 0.0:
                moving_avg_price += value
            # Normal transaction
            elif isinstance(value, ComputedTransaction):
                moving_avg_price = round(
                    ((total_quantity * moving_avg_price) + (value.quantity * value.share_price)) /
                    (total_quantity + value.quantity),
                    4)
                value.moving_avg_price = moving_avg_price

                if value.date <= config.oekb_report_date:
                    total_quantity_before_report = round(total_quantity_before_report + value.quantity, 3)

                total_quantity = round(total_quantity + value.quantity, 3)

        return total_quantity, total_quantity_before_report, moving_avg_price

    def _calculate_fund_totals(self, config: Config, ecb_exchange_rate: float,
                               total_quantity_before_report: float) -> Tuple[float, float]:
        """Calculate the final totals for a fund."""
        distribution_equivalent_income = self._compute_distribution_equivalent_income(
            config, ecb_exchange_rate, total_quantity_before_report)
        taxes_paid_abroad = self._compute_taxes_paid_abroad(
            config, ecb_exchange_rate, total_quantity_before_report)

        return distribution_equivalent_income, taxes_paid_abroad
