"""
Excel report generator for Austrian investment fund tax calculations.
Creates detailed Excel workbooks with transaction data and tax calculations.
"""
from typing import List

import pandas as pd

from scalable_capital.models import TaxCalculationResult, SecurityType


class ExcelReportGenerator:
    """Create an Excel workbook summarising all tax calculations."""

    def __init__(self, tax_results: List[TaxCalculationResult]):
        """Store the list of calculation results to export."""
        self.tax_results = tax_results

    def _create_transaction_df(self, result: TaxCalculationResult) -> pd.DataFrame:
        """Return a DataFrame listing all transactions for ``result``."""
        data = []

        # Add initial position with starting date, quantity, and moving avg price
        data.append({
            'Date': pd.to_datetime(result.start_date),
            'Type': 'START',  # Add type for initial position
            'Quantity': round(result.starting_quantity, 3),
            'Share Price': 0,
            'Total Price': 0,
            'Moving Avg Price': round(result.starting_moving_avg_price, 4),
            'Total Quantity': round(result.starting_quantity, 3)  # Initial total quantity
        })

        for t in result.computed_transactions:
            transaction_data = {
                'Date': pd.to_datetime(t.date),
                'Type': t.type_name(),
                'Quantity': round(t.quantity, 3) if hasattr(t, 'quantity') else 0,
                'Share Price': round(t.share_price, 3) if hasattr(t, 'share_price') else 0,
                'Total Price': round(t.total_price(), 4) if hasattr(t, 'total_price') else 0,
                'Moving Avg Price': round(t.moving_avg_price, 4) if hasattr(t, 'moving_avg_price') else 0,
                'Total Quantity': round(t.total_quantity, 3)
            }
            data.append(transaction_data)

        df = pd.DataFrame(data)
        return df

    def _create_tax_summary_df(self, result: TaxCalculationResult) -> List[pd.DataFrame]:
        """Build the summary sections for ``result`` as a list of DataFrames."""
        # Basic Information - Common for all security types
        basic_info_metrics = ['ISIN', 'Security Type', 'Start Date', 'End Date']
        basic_info_values = [
            result.isin,
            result.security_type.value,
            pd.to_datetime(result.start_date),
            pd.to_datetime(result.end_date),
        ]

        # Add report date only for accumulating ETFs that reported
        if result.security_type == SecurityType.ACCUMULATING_ETF and result.report_date is not None:
            basic_info_metrics.append('Report Date')
            basic_info_values.append(pd.to_datetime(result.report_date))

        basic_info = {
            'Metric': basic_info_metrics,
            'Value': basic_info_values
        }

        # Quantity Information - Common for all security types
        quantity_info_metrics = ['Starting Quantity', 'Total Quantity']
        quantity_info_values = [
            round(result.starting_quantity, 3),
            round(result.total_quantity, 3)
        ]

        # Add quantity before report only for accumulating ETFs
        if result.security_type == SecurityType.ACCUMULATING_ETF:
            quantity_info_metrics.insert(1, 'Total Quantity Before Report')
            quantity_info_values.insert(1, round(result.total_quantity_before_report, 3))

        quantity_info = {
            'Metric': quantity_info_metrics,
            'Value': quantity_info_values
        }

        # Initialize sections list with common information
        sections = [
            ('Basic Information', pd.DataFrame(basic_info)),
            ('Quantity Information', pd.DataFrame(quantity_info)),
        ]

        # Price Information - Different for each security type
        price_info_metrics = ['Starting Moving Avg Price', 'Final Moving Avg Price']
        price_info_values = [
            round(result.starting_moving_avg_price, 4),
            round(result.final_moving_avg_price, 4),
        ]

        if result.security_type == SecurityType.ACCUMULATING_ETF:
            price_info_metrics.append(f'ECB Exchange Rate ({result.report_currency} → EUR)')
            price_info_values.append(round(result.ecb_exchange_rate, 4))

        price_info = {
            'Metric': price_info_metrics,
            'Value': price_info_values
        }
        sections.append(('Price Information', pd.DataFrame(price_info)))

        # OeKB Factors - Only for accumulating ETFs
        if result.security_type == SecurityType.ACCUMULATING_ETF:
            oekb_factors = {
                'Metric': [
                    'Distribution Equivalent Income Factor',
                    'Taxes Paid Abroad Factor',
                    'Adjustment Factor'
                ],
                'Value': [
                    round(result.distribution_equivalent_income_factor, 4),
                    round(result.taxes_paid_abroad_factor, 4),
                    round(result.adjustment_factor, 4),
                ]
            }
            sections.append(('OeKB Factors', pd.DataFrame(oekb_factors)))

        # Tax Results - Different for each security type
        tax_results_metrics = []
        tax_results_values = []

        if result.security_type == SecurityType.ACCUMULATING_ETF:
            tax_results_metrics.extend([
                'Distribution Equivalent Income (EUR)',
                'Taxes Paid Abroad (EUR)',
            ])
            tax_results_values.extend([
                round(result.distribution_equivalent_income, 2),
                round(result.taxes_paid_abroad, 2),
            ])

        # Total Capital Gains is common for all security types
        tax_results_metrics.append('Total Capital Gains (EUR)')
        tax_results_values.append(round(result.total_capital_gains, 2))

        tax_results = {
            'Metric': tax_results_metrics,
            'Value': tax_results_values
        }
        sections.append(('Tax Results', pd.DataFrame(tax_results)))

        return sections

    def generate_report(self, output_path: str) -> None:
        """Write an Excel file with one sheet per ISIN."""
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Create formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })

            cell_format = workbook.add_format({
                'border': 1
            })

            number_format_3d = workbook.add_format({
                'num_format': '0.000',
                'border': 1
            })

            number_format_4d = workbook.add_format({
                'num_format': '0.0000',
                'border': 1
            })

            number_format_2d = workbook.add_format({
                'num_format': '0.00',
                'border': 1
            })

            date_format = workbook.add_format({
                'num_format': 'dd/mm/yyyy',
                'border': 1,
                'align': 'center'
            })

            # Add a title format
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'bg_color': '#4F81BD',
                'font_color': 'white',
                'align': 'center',
                'border': 1
            })

            # Generate sheets for each tax result
            for result in self.tax_results:
                year_suffix = f"_{pd.to_datetime(result.start_date).strftime('%Y')}"
                isin = result.isin

                # Create transaction sheet
                trans_df = self._create_transaction_df(result)
                if not trans_df.empty:
                    sheet_name = f'{isin}_transactions{year_suffix}'
                    trans_df.to_excel(writer, sheet_name=sheet_name, index=False)

                    # Format the sheet
                    worksheet = writer.sheets[sheet_name]

                    # Apply formats to all rows
                    for row in range(1, len(trans_df) + 1):
                        date_val = trans_df.iloc[row - 1]['Date']
                        excel_date = date_val.timestamp() / 86400 + 25569  # Convert to Excel date format
                        worksheet.write(row, 0, excel_date, date_format)
                        worksheet.write(row, 1, trans_df.iloc[row - 1]['Type'], cell_format)  # Add Type column
                        worksheet.write(row, 2, trans_df.iloc[row - 1]['Quantity'], number_format_3d)
                        worksheet.write(row, 3, trans_df.iloc[row - 1]['Share Price'], number_format_3d)
                        worksheet.write(row, 4, trans_df.iloc[row - 1]['Total Price'], number_format_4d)
                        worksheet.write(row, 5, trans_df.iloc[row - 1]['Moving Avg Price'], number_format_4d)

                    # Set column widths
                    worksheet.set_column('A:A', 12)  # Date
                    worksheet.set_column('B:B', 8)  # Type
                    worksheet.set_column('C:C', 12)  # Quantity
                    worksheet.set_column('D:D', 12)  # Share Price
                    worksheet.set_column('E:F', 12)  # Total Price and Moving Avg Price

                    # Apply header format
                    for col_num, value in enumerate(trans_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)

                # Create tax summary sheet with sections
                summary_sections = self._create_tax_summary_df(result)
                if summary_sections:
                    sheet_name = f'{isin}_summary{year_suffix}'
                    worksheet = workbook.add_worksheet(sheet_name)

                    current_row = 0

                    for section_title, df in summary_sections:
                        # Write section title
                        worksheet.merge_range(current_row, 0, current_row, 1, section_title, title_format)
                        current_row += 1

                        # Write headers
                        for col_num, value in enumerate(df.columns.values):
                            worksheet.write(current_row, col_num, value, header_format)
                        current_row += 1

                        # Write data
                        for row_num, (_, row) in enumerate(df.iterrows(), start=current_row):
                            worksheet.write(row_num, 0, row['Metric'], cell_format)
                            value = row['Value']

                            # Apply appropriate format based on the metric type
                            metric = row['Metric']
                            if metric in ['Start Date', 'End Date', 'Report Date']:
                                excel_date = pd.to_datetime(value).timestamp() / 86400 + 25569
                                worksheet.write(row_num, 1, excel_date, date_format)
                            elif metric in ['Starting Quantity', 'Quantity at Report Date',
                                            'Final Quantity']:
                                worksheet.write(row_num, 1, value, number_format_3d)
                            elif metric in ['Distribution Equivalent Income (EUR) (936/937)',
                                            'Taxes Paid Abroad (EUR) (984/998)']:
                                worksheet.write(row_num, 1, value, number_format_2d)
                            elif metric == 'ISIN':
                                worksheet.write(row_num, 1, value, cell_format)
                            else:
                                worksheet.write(row_num, 1, value, number_format_4d)

                        current_row += len(df) + 1  # Add extra row for spacing between sections

                    # Set column widths
                    worksheet.set_column('A:A', 35)
                    worksheet.set_column('B:B', 20)


def generate_excel_report(tax_results: List[TaxCalculationResult], output_path: str):
    """Generate an Excel report for ``tax_results`` and save it to ``output_path``."""
    generator = ExcelReportGenerator(tax_results)
    generator.generate_report(output_path)
