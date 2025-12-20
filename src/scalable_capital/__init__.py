"""
Scalable Capital AT Tax Report - Austrian investment fund tax calculator.

This package provides tools for calculating Austrian tax obligations on investment funds
traded through Scalable Capital, including support for accumulating ETFs with OeKB reports.
"""

from scalable_capital.tax_calculator import TaxCalculator
from scalable_capital.excel_report import generate_excel_report
from scalable_capital.terminal_report import generate_terminal_report

__all__ = [
    "TaxCalculator",
    "generate_excel_report",
    "generate_terminal_report",
]

__version__ = "1.0.0"


