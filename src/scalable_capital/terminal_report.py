"""
Terminal report generator for Austrian investment fund tax calculations.
Creates detailed console output with transaction data and tax calculations.
"""
from typing import List

from scalable_capital.models import Config, TaxCalculationResult, AdjustmentTransaction, ComputedTransaction, \
    BuyTransaction, SellTransaction, SecurityType


class TerminalReportGenerator:
    """Generates formatted terminal output for tax calculation results."""

    @staticmethod
    def print_fund_details(config: Config, ecb_exchange_rate: float, csv_file_path: str) -> None:
        """Print the details of a fund including OeKB factors and exchange rate."""
        print("\n" + "=" * 80)
        print(f"{'DETAILS':^80}")
        print("=" * 80 + "\n")

        print(f"Config ISIN: {config.isin}")
        print(f"Security Type: {config.security_type.value}")
        print(f"Data file: {csv_file_path}\n")

        # Only show OEKB factors for accumulating ETFs and when a report is there
        if config.security_type == SecurityType.ACCUMULATING_ETF and config.oekb_report_date is not None:
            print("OeKB Factors:")
            print(f"  • Distribution equivalent income: {config.oekb_distribution_equivalent_income_factor:.4f}")
            print(f"  • Taxes paid abroad: {config.oekb_taxes_paid_abroad_factor:.4f}")
            print(f"  • Adjustment: {config.oekb_adjustment_factor:.4f}\n")

            print(
                f"ECB Exchange rate ({config.oekb_report_currency} → EUR) at {config.oekb_report_date.strftime('%d/%m/%Y')}: {ecb_exchange_rate:.4f}")

    @staticmethod
    def print_transactions(config: Config, computed_transactions: List[ComputedTransaction]) -> None:
        """Print the transaction details including headers and computed values."""
        print("\n" + "=" * 90)
        print(f"{'TRANSACTIONS':^90}")
        print("=" * 90 + "\n")

        # Print header with proper spacing
        print(
            f"{'Date':12} {'Type':8} {'Quantity':>12} {'Share Price':>14} {'Total Price':>14} {'Moving Avg':>14} {'Total Qty':>12}")
        print("-" * 90)

        # Print starting quantity and starting moving average price
        print(
            f"{config.start_date.strftime('%d/%m/%Y'):12} {'START':8} {config.starting_quantity:>12.3f} "
            f"{'N/A':>14} {'N/A':>14} {config.starting_moving_avg_price:>14.4f} {config.starting_quantity:>12.3f}")

        # Print all transactions
        for value in computed_transactions:
            if isinstance(value, AdjustmentTransaction):
                print(
                    f"{value.date.strftime('%d/%m/%Y'):12} {value.type_name():8} {0.0:>12.3f} "
                    f"{0.0:>14.3f} {value.total_price():>14.4f} {value.moving_avg_price:>14.4f} "
                    f"{value.total_quantity:>12.3f}")
            elif isinstance(value, (BuyTransaction, SellTransaction)):
                print(
                    f"{value.date.strftime('%d/%m/%Y'):12} {value.type_name():8} {value.quantity:>12.3f} "
                    f"{value.share_price:>14.3f} {value.total_price():>14.4f} {value.moving_avg_price:>14.4f} "
                    f"{value.total_quantity:>12.3f}")

    @staticmethod
    def print_capital_gains(distribution_equivalent_income: float, taxes_paid_abroad: float,
                            total_capital_gains: float) -> None:
        """Print the capital gains information."""
        print("\n" + "=" * 80)
        print(f"{'CAPITAL GAINS':^80}")
        print("=" * 80 + "\n")

        # We have to round to 2 decimals since this is what Finanzonline expects
        dei = round(distribution_equivalent_income, 2)
        tpa = round(taxes_paid_abroad, 2)
        cg = round(total_capital_gains, 2)
        print(f"{'Distribution equivalent income (936/937):':<50} {dei:>10.2f} EUR")
        print(f"{'Taxes paid abroad (984/998):':<50} {tpa:>10.2f} EUR")
        print(f"{'Capital gains:':<50} {cg:>10.2f} EUR")

    @staticmethod
    def print_stats(config: Config, total_quantity_before_report: float, total_quantity: float) -> None:
        """Print statistics about share quantities."""
        print("\n" + "=" * 80)
        print(f"{'STATS':^80}")
        print("=" * 80 + "\n")

        print(f"Starting shares:                              {config.starting_quantity:,.3f}")
        if config.security_type == SecurityType.ACCUMULATING_ETF and config.oekb_report_date is not None:
            print(
                f"Total shares before OeKB report ({config.oekb_report_date.strftime('%d/%m/%Y')}): {total_quantity_before_report:,.3f}")
        print(f"Current total shares:                         {total_quantity:,.3f}")

    @staticmethod
    def print_final_summary(total_distribution_equivalent_income: float, total_taxes_paid_abroad: float, total_capital_gains: float) -> None:
        """Print the final summary of all calculations."""
        print("\n" + "=" * 80)
        print(f"{'FINAL SUMMARY (ALL SECURITIES)':^80}")
        print("=" * 80 + "\n")

        # We have to round to 2 decimals since this is what Finanzonline expects
        dei = round(total_distribution_equivalent_income, 2)
        tpa = round(total_taxes_paid_abroad, 2)
        cg = round(total_capital_gains, 2)
        projected = round(((total_distribution_equivalent_income + total_capital_gains) * 0.275) - total_taxes_paid_abroad, 2)

        print(f"{'Distribution equivalent income (936/937):':<50} {dei:>10.2f} EUR")
        print(f"{'Taxes paid abroad (984/998):':<50} {tpa:>10.2f} EUR")
        print(f"{'Total capital gains:':<50} {cg:>10.2f} EUR")
        print(f"\n{'Projected taxes to pay:':<50} {projected:>10.2f} EUR")
        print("\nNote: All amounts are rounded to 2 decimal places as required by Finanzonline.")


def generate_terminal_report(tax_results: List[TaxCalculationResult], csv_file_path: str) -> None:
    """Generate terminal output for tax calculation results."""
    generator = TerminalReportGenerator()
    total_distribution_equivalent_income = 0
    total_taxes_paid_abroad = 0
    total_capital_gains = 0

    for result in tax_results:
        # Print fund details
        generator.print_fund_details(
            Config(
                start_date=result.start_date,
                end_date=result.end_date,
                oekb_report_date=result.report_date,
                oekb_distribution_equivalent_income_factor=result.distribution_equivalent_income_factor,
                oekb_taxes_paid_abroad_factor=result.taxes_paid_abroad_factor,
                oekb_adjustment_factor=result.adjustment_factor,
                oekb_report_currency=result.report_currency,
                starting_quantity=result.starting_quantity,
                starting_moving_avg_price=result.starting_moving_avg_price,
                isin=result.isin,
                security_type=result.security_type
            ),
            result.ecb_exchange_rate,
            csv_file_path
        )

        # Print transactions
        generator.print_transactions(
            Config(
                start_date=result.start_date,
                end_date=result.end_date,
                oekb_report_date=result.report_date,
                oekb_distribution_equivalent_income_factor=result.distribution_equivalent_income_factor,
                oekb_taxes_paid_abroad_factor=result.taxes_paid_abroad_factor,
                oekb_adjustment_factor=result.adjustment_factor,
                oekb_report_currency=result.report_currency,
                starting_quantity=result.starting_quantity,
                starting_moving_avg_price=result.starting_moving_avg_price,
                isin=result.isin,
                security_type=result.security_type
            ),
            result.computed_transactions
        )

        # Print capital gains
        generator.print_capital_gains(
            result.distribution_equivalent_income,
            result.taxes_paid_abroad,
            result.total_capital_gains
        )

        # Print stats
        generator.print_stats(
            Config(
                start_date=result.start_date,
                end_date=result.end_date,
                oekb_report_date=result.report_date,
                oekb_distribution_equivalent_income_factor=result.distribution_equivalent_income_factor,
                oekb_taxes_paid_abroad_factor=result.taxes_paid_abroad_factor,
                oekb_adjustment_factor=result.adjustment_factor,
                oekb_report_currency=result.report_currency,
                starting_quantity=result.starting_quantity,
                starting_moving_avg_price=result.starting_moving_avg_price,
                isin=result.isin,
                security_type=result.security_type
            ),
            result.total_quantity_before_report,
            result.total_quantity
        )

        total_distribution_equivalent_income += result.distribution_equivalent_income
        total_taxes_paid_abroad += result.taxes_paid_abroad
        total_capital_gains += result.total_capital_gains

    # Print final summary
    generator.print_final_summary(total_distribution_equivalent_income, total_taxes_paid_abroad, total_capital_gains)
