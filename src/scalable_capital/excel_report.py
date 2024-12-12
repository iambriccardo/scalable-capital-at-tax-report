"""
Excel report generator for Austrian investment fund tax calculations.
Creates detailed Excel workbooks with transaction data and tax calculations.
"""
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal

from scalable_capital.models import TaxCalculationResult, ComputedTransaction


class ExcelReportGenerator:
    def __init__(self, tax_results: List[TaxCalculationResult]):
        """Initialize the Excel report generator with a list of calculation results."""
        self.tax_results = tax_results

    def _create_transaction_df(self, result: TaxCalculationResult) -> pd.DataFrame:
        """Create a DataFrame with transactions for a specific ISIN from a tax result."""
        data = []
        
        # Add initial position with starting date, quantity, and moving avg price
        data.append({
            'Date': result.start_date,
            'Quantity': round(result.starting_quantity, 3),
            'Share Price': None,
            'Total Price': None,
            'Moving Avg Price': round(result.starting_moving_avg_price, 4)
        })
        
        for t in result.computed_transactions:
            if isinstance(t, ComputedTransaction):
                data.append({
                    'Date': t.date,
                    'Quantity': round(t.quantity, 3),
                    'Share Price': round(t.share_price, 3),
                    'Total Price': round(t.total_price, 4),
                    'Moving Avg Price': round(t.moving_avg_price, 4)
                })
        
        df = pd.DataFrame(data)
        return df.sort_values('Date')

    def _create_tax_summary_df(self, result: TaxCalculationResult) -> pd.DataFrame:
        """Create a DataFrame with tax calculation summary for a specific ISIN from a tax result."""
        data = {
            'Metric': [
                'Report Date',
                'Starting Quantity',
                'Quantity at Report Date',
                'Final Quantity',
                'Starting Moving Avg Price',
                'Final Moving Avg Price',
                'ECB Exchange Rate',
                'Distribution Equivalent Income Factor',
                'Taxes Paid Abroad Factor',
                'Adjustment Factor',
                'Distribution Equivalent Income (EUR)',
                'Taxes Paid Abroad (EUR)',
            ],
            'Value': [
                result.report_date.strftime('%Y-%m-%d'),
                round(result.starting_quantity, 3),
                round(result.quantity_at_report, 3),
                round(result.final_quantity, 3),
                round(result.starting_moving_avg_price, 4),
                round(result.final_moving_avg_price, 4),
                round(result.ecb_exchange_rate, 4),
                round(result.distribution_equivalent_income_factor, 4),
                round(result.taxes_paid_abroad_factor, 4),
                round(result.adjustment_factor, 4),
                round(result.distribution_equivalent_income, 2),  # Finanzonline requires 2 decimals
                round(result.taxes_paid_abroad, 2),  # Finanzonline requires 2 decimals
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
            
            # Different number formats for different precisions
            number_format_3d = workbook.add_format({
                'num_format': '#,##0.000',  # 3 decimal places for quantities
                'border': 1
            })
            
            number_format_4d = workbook.add_format({
                'num_format': '#,##0.0000',  # 4 decimal places for prices
                'border': 1
            })
            
            number_format_2d = workbook.add_format({
                'num_format': '#,##0.00',  # 2 decimal places for EUR amounts
                'border': 1
            })
            
            date_format = workbook.add_format({
                'num_format': 'dd/mm/yyyy',  # Match the date format from tax calculator
                'border': 1
            })
            
            # Generate sheets for each tax result
            for result in self.tax_results:
                year_suffix = f"_{result.report_date.strftime('%Y')}"
                isin = result.isin
                
                # Create transaction sheet
                trans_df = self._create_transaction_df(result)
                if not trans_df.empty:
                    sheet_name = f'{isin}_transactions{year_suffix}'
                    trans_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Format the sheet
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 12, date_format)  # Date
                    worksheet.set_column('B:B', 12, number_format_3d)  # Quantity
                    worksheet.set_column('C:C', 12, number_format_3d)  # Share Price
                    worksheet.set_column('D:E', 12, number_format_4d)  # Total Price and Moving Avg
                    
                    # Apply header format
                    for col_num, value in enumerate(trans_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                
                # Create tax summary sheet
                tax_df = self._create_tax_summary_df(result)
                if not tax_df.empty:
                    sheet_name = f'{isin}_summary{year_suffix}'
                    tax_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Format the summary sheet
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:A', 35)
                    worksheet.set_column('B:B', 20)
                    
                    # Apply header format
                    for col_num, value in enumerate(tax_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)

def generate_excel_report(tax_results: List[TaxCalculationResult], output_path: str):
    """Convenience function to generate an Excel report."""
    generator = ExcelReportGenerator(tax_results)
    generator.generate_report(output_path) 