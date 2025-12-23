"""Application state management for the TUI."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from scalable_capital.models import Config, TaxCalculationResult
from scalable_capital.constants import DEFAULT_FILE_ENCODING


@dataclass
class TUIState:
    """Central application state for the TUI."""

    # File paths
    transaction_file: Optional[str] = None
    config_file: Optional[str] = None
    excel_output: Optional[str] = None

    # Configurations
    configs: List[Config] = field(default_factory=list)

    # Results
    results: Optional[List[TaxCalculationResult]] = None

    # UI State
    editing_config_index: Optional[int] = None

    def add_config(self, config: Config) -> None:
        """Add a new configuration to the list."""
        self.configs.append(config)

    def update_config(self, index: int, config: Config) -> None:
        """Update an existing configuration at the given index."""
        if 0 <= index < len(self.configs):
            self.configs[index] = config

    def remove_config(self, index: int) -> None:
        """Remove a configuration at the given index."""
        if 0 <= index < len(self.configs):
            self.configs.pop(index)

    def get_config_by_isin(self, isin: str) -> Optional[Config]:
        """Find a configuration by ISIN."""
        for config in self.configs:
            if config.isin == isin:
                return config
        return None

    def clear_configs(self) -> None:
        """Clear all configurations."""
        self.configs = []

    def save_to_json(self, path: str) -> None:
        """Save configurations to a JSON file."""
        config_dicts = [self._config_to_dict(c) for c in self.configs]
        with open(path, 'w', encoding=DEFAULT_FILE_ENCODING) as f:
            json.dump(config_dicts, f, indent=2)

    def load_from_json(self, path: str) -> None:
        """Load configurations from a JSON file."""
        with open(path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
            config_data = json.load(f)
            self.configs = [Config.from_dict(c) for c in config_data]
            self.config_file = path

    @staticmethod
    def _config_to_dict(config: Config) -> dict:
        """Convert a Config object to a dictionary for JSON serialization."""
        result = {
            'type': config.security_type.value,
            'start_date': config.start_date.strftime('%d/%m/%Y'),
            'end_date': config.end_date.strftime('%d/%m/%Y'),
            'isin': config.isin,
            'starting_quantity': config.starting_quantity,
            'starting_moving_avg_price': config.starting_moving_avg_price,
        }

        # Add OeKB fields if report date is set (meaning it's an ETF with OeKB data)
        # Include all OeKB fields to preserve the complete configuration
        if config.oekb_report_date is not None:
            result['oekb_report_date'] = config.oekb_report_date.strftime('%d/%m/%Y')
            result['oekb_distribution_equivalent_income_factor'] = config.oekb_distribution_equivalent_income_factor
            result['oekb_taxes_paid_abroad_factor'] = config.oekb_taxes_paid_abroad_factor
            result['oekb_adjustment_factor'] = config.oekb_adjustment_factor
            if config.oekb_report_currency is not None:
                result['oekb_report_currency'] = config.oekb_report_currency

        return result

    def reset(self) -> None:
        """Reset the state to initial values."""
        self.transaction_file = None
        self.config_file = None
        self.excel_output = None
        self.configs = []
        self.results = None
        self.editing_config_index = None
