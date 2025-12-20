"""
Main entry point for the Austrian investment fund tax calculator.
Terminal User Interface (TUI) for interactive tax calculations.
"""
from scalable_capital.tui.app import TaxCalculatorApp


def main():
    """
    Main entry point for the TUI tax calculator.

    Launches the Textual-based Terminal User Interface for an interactive
    tax calculation experience.
    """
    app = TaxCalculatorApp()
    app.run()


if __name__ == '__main__':
    main()


# ==============================================================================
# OLD CLI CODE (PRESERVED FOR REFERENCE)
# ==============================================================================
# The following CLI code has been replaced with the TUI implementation above.
# It is kept here for reference and potential future CLI restoration if needed.
# ==============================================================================
"""
# import json
# import os
# import sys
# import csv
# from typing import List
#
# from scalable_capital.excel_report import generate_excel_report
# from scalable_capital.models import Config
# from scalable_capital.tax_calculator import TaxCalculator
# from scalable_capital.terminal_report import generate_terminal_report
# from scalable_capital.json_converter import convert_json_to_csv
# from scalable_capital.constants import DEFAULT_FILE_ENCODING, CSV_DELIMITER, CSV_PREVIEW_LINES
# from scalable_capital.exceptions import ConfigurationError, FileConversionError
#
#
# def load_configs(config_path: str) -> List[Config]:
#     try:
#         with open(config_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
#             config_data = json.load(f)
#             return [Config.from_dict(c) for c in config_data]
#     except (json.JSONDecodeError, KeyError, ValueError) as e:
#         raise ConfigurationError(f"Invalid configuration file: {str(e)}") from e
#
#
# def is_json_file(file_path: str) -> bool:
#     if file_path.lower().endswith('.json'):
#         return True
#     try:
#         with open(file_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
#             json.load(f)
#         return True
#     except (json.JSONDecodeError, UnicodeDecodeError):
#         return False
#
# [... rest of CLI code omitted for brevity ...]
"""
