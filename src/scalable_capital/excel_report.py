"""
Excel report generator for Austrian investment fund tax calculations.
Creates detailed Excel workbooks with transaction data and tax calculations.
"""
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal

from scalable_capital.models import Config, Transaction
from scalable_capital.tax_calculator import TaxCalculator


class ExcelReportGenerator:
    def __init__(self, calculator: TaxCalculator):
        """Initialize the Excel report generator with a TaxCalculator instance."""
        self.calculator = calculator
        self.configs = calculator.configs
        self.transactions = calculator.transactions

    def _create_transaction_df(self, isin: str) -> pd.DataFrame:
        """Create a DataFrame with transactions for a specific ISIN."""
        isin_transactions = [t for t in self.transactions if t.isin == isin]
        
        if not isin_transactions:
            return pd.DataFrame()
        
        data = []
        for t in isin_transactions:
            data.append({
                'Date': t.date,
                'Time': t.time,
                'Type': t.type.value,
                'Shares': float(t.shares),
                'Price': float(t.price),
                'Amount': float(t.amount),
                'Fee': float(t.fee),
                'Tax': float(t.tax),
                'Currency': t.currency,
                'Status': t.status,
                'Reference': t.reference
            })
        
        df = pd.DataFrame(data)
        return df.sort_values('Date')

    def _create_tax_summary_df(self, config: Config) -> pd.DataFrame:
        """Create a DataFrame with tax calculation summary for a specific ISIN."""
        # Get ECB exchange rate for the report date
        from currency_converter import CurrencyConverter
        ecb_rate = CurrencyConverter().convert(1, config.oekb_report_currency, date=config.oekb_report_date)
        
        # Calculate quantities
        isin_transactions = [t for t in self.transactions if t.isin == config.isin]
        quantity = config.starting_quantity
        for t in isin_transactions:
            if t.date <= config.oekb_report_date and t.type.is_buy():
                quantity += float(t.shares)
            elif t.date <= config.oekb_report_date and t.type == "SELL":
                quantity -= float(t.shares)

        # Calculate tax values
        dei = self.calculator._compute_distribution_equivalent_income(config, ecb_rate, quantity)
        tpa = self.calculator._compute_taxes_paid_abroad(config, ecb_rate, quantity)
        adj = self.calculator._compute_adjustment_factor(config, ecb_rate)
        
        data = {
            'Metric': [
                'Report Date',
                'Starting Quantity',
                'Quantity at Report Date',
                'Starting Moving Avg Price',
                'ECB Exchange Rate',
                'Distribution Equivalent Income Factor',
                'Taxes Paid Abroad Factor',
                'Adjustment Factor',
                'Distribution Equivalent Income (EUR)',
                'Taxes Paid Abroad (EUR)',
                'Projected Tax Payment (EUR)'
            ],
            'Value': [
                config.oekb_report_date.strftime('%Y-%m-%d'),
                config.starting_quantity,
                quantity,
                config.starting_moving_avg_price,
                ecb_rate,
                config.oekb_distribution_equivalent_income_factor,
                config.oekb_taxes_paid_abroad_factor,
                adj,
                dei,
                tpa,
                (dei * 0.275) - tpa
            ]
        }
        
        return pd.DataFrame(data)

    def generate_report(self, output_path: str):
        """Generate an Excel report with transactions and tax calculations per ISIN."""
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Create formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1
            })
            
            date_format = workbook.add_format({
                'num_format': 'yyyy-mm-dd',
                'border': 1
            })
            
            # Generate sheets for each ISIN
            for config in self.configs:
                # Create transaction sheet
                trans_df = self._create_transaction_df(config.isin)
                if not trans_df.empty:
                    sheet_name = f'{config.isin}_transactions'
                    trans_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Format the sheet
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 12, date_format)  # Date
                    worksheet.set_column('B:B', 10)  # Time
                    worksheet.set_column('C:C', 15)  # Type
                    worksheet.set_column('D:F', 12, number_format)  # Shares, Price, Amount
                    worksheet.set_column('G:H', 10, number_format)  # Fee, Tax
                    worksheet.set_column('I:I', 8)  # Currency
                    worksheet.set_column('J:K', 15)  # Status, Reference
                    
                    # Apply header format
                    for col_num, value in enumerate(trans_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                
                # Create tax summary sheet
                tax_df = self._create_tax_summary_df(config)
                sheet_name = f'{config.isin}_summary'
                tax_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format the summary sheet
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 35)
                worksheet.set_column('B:B', 20)
                
                # Apply header format
                for col_num, value in enumerate(tax_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)


def generate_excel_report(configs: List[Config], transactions_path: str, output_path: str):
    """Convenience function to generate an Excel report."""
    calculator = TaxCalculator(configs, transactions_path)
    generator = ExcelReportGenerator(calculator)
    generator.generate_report(output_path) 