"""
Custom exception classes for the Scalable Capital AT Tax Report application.

These exceptions provide better error handling and more informative error messages
to help users understand and resolve issues.
"""


class TaxReportError(Exception):
    """Base exception for all tax report errors."""
    pass


class ConfigurationError(TaxReportError):
    """Raised when there's an error in the configuration."""
    pass


class ValidationError(TaxReportError):
    """Raised when input validation fails."""
    pass


class TransactionDataError(TaxReportError):
    """Raised when there's an error processing transaction data."""
    pass


class CalculationError(TaxReportError):
    """Raised when there's an error during tax calculations."""
    pass


class FileConversionError(TaxReportError):
    """Raised when there's an error converting between file formats."""
    pass


class ReportGenerationError(TaxReportError):
    """Raised when there's an error generating a report."""
    pass
