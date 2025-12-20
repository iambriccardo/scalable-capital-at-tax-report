"""Config form screen for adding/editing a security configuration."""
from datetime import datetime
from typing import Optional, Callable

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Label, Input, Select

from scalable_capital.models import Config, SecurityType
from scalable_capital.exceptions import ValidationError


class ConfigFormScreen(Screen):
    """Screen for adding or editing a security configuration."""

    def __init__(self, config: Optional[Config] = None, on_save: Optional[Callable] = None):
        super().__init__()
        self.config = config
        self.on_save = on_save
        self.is_edit = config is not None

    def compose(self) -> ComposeResult:
        """Compose the config form screen."""
        with Container(classes="container"):
            with Vertical():
                title = "Edit Security" if self.is_edit else "Add Security"
                yield Static(f"[bold]{title}[/]", classes="header")

                with ScrollableContainer():
                    with Vertical(classes="form-field"):
                        yield Label("\n[bold]General Information[/]")

                        yield Label("ISIN (12 characters):", classes="help-text")
                        yield Input(
                            placeholder="e.g., IE00B4L5Y983",
                            id="isin",
                            value=self.config.isin if self.config else ""
                        )

                        yield Label("Security Type:", classes="help-text")
                        yield Select(
                            options=[
                                ("Accumulating ETF", "accumulating_etf"),
                                ("Stock", "stock")
                            ],
                            id="security-type",
                            value=self.config.security_type.value if self.config else "accumulating_etf"
                        )

                        yield Label("Start Date (DD/MM/YYYY):", classes="help-text")
                        yield Input(
                            placeholder="01/01/2024",
                            id="start-date",
                            value=self.config.start_date.strftime('%d/%m/%Y') if self.config else ""
                        )

                        yield Label("End Date (DD/MM/YYYY):", classes="help-text")
                        yield Input(
                            placeholder="31/12/2024",
                            id="end-date",
                            value=self.config.end_date.strftime('%d/%m/%Y') if self.config else ""
                        )

                        yield Label("Starting Quantity:", classes="help-text")
                        yield Input(
                            placeholder="0.000",
                            id="starting-quantity",
                            value=str(self.config.starting_quantity) if self.config else "0.0"
                        )

                        yield Label("Starting Moving Average Price:", classes="help-text")
                        yield Input(
                            placeholder="0.0000",
                            id="starting-price",
                            value=str(self.config.starting_moving_avg_price) if self.config else "0.0"
                        )

                        yield Label("\n[bold]OeKB Data (for ETFs only)[/]", id="oekb-header")
                        yield Label("Leave empty if not applicable", classes="help-text", id="oekb-help")

                        yield Label("OeKB Report Date (DD/MM/YYYY, optional):", classes="help-text", id="oekb-date-label")
                        yield Input(
                            placeholder="17/08/2024",
                            id="oekb-date",
                            value=self.config.oekb_report_date.strftime('%d/%m/%Y') if self.config and self.config.oekb_report_date else ""
                        )

                        yield Label("Distribution Equivalent Income Factor:", classes="help-text", id="dei-label")
                        yield Input(
                            placeholder="0.0000",
                            id="dei-factor",
                            value=str(self.config.oekb_distribution_equivalent_income_factor) if self.config else "0.0"
                        )

                        yield Label("Taxes Paid Abroad Factor:", classes="help-text", id="tpa-label")
                        yield Input(
                            placeholder="0.0000",
                            id="tpa-factor",
                            value=str(self.config.oekb_taxes_paid_abroad_factor) if self.config else "0.0"
                        )

                        yield Label("Adjustment Factor:", classes="help-text", id="adj-label")
                        yield Input(
                            placeholder="0.0000",
                            id="adj-factor",
                            value=str(self.config.oekb_adjustment_factor) if self.config else "0.0"
                        )

                        yield Label("Report Currency (e.g., USD, EUR):", classes="help-text", id="currency-label")
                        yield Input(
                            placeholder="USD",
                            id="currency",
                            value=self.config.oekb_report_currency if self.config and self.config.oekb_report_currency else ""
                        )

                        yield Label("", id="error-message", classes="error-text")

                with Horizontal():
                    yield Button("Cancel", id="cancel", variant="default")
                    yield Button("Validate", id="validate", variant="default")
                    yield Button("Save", id="save", variant="success")

                yield Static("", classes="footer", id="status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "validate":
            self._validate_form()
        elif event.button.id == "save":
            if self._save_config():
                self.app.pop_screen()
                if self.on_save:
                    self.on_save()

    def _validate_form(self) -> bool:
        """Validate the form and show errors."""
        error_label = self.query_one("#error-message", Label)
        error_label.update("")

        try:
            config_dict = self._gather_form_data()
            Config.from_dict(config_dict)
            self.app.notify("Validation successful!", severity="information")
            return True
        except ValidationError as e:
            error_label.update(f"Validation Error: {str(e)}")
            self.app.notify("Validation failed", severity="error")
            return False
        except Exception as e:
            error_label.update(f"Error: {str(e)}")
            self.app.notify("Error in form data", severity="error")
            return False

    def _save_config(self) -> bool:
        """Save the configuration."""
        try:
            config_dict = self._gather_form_data()
            config = Config.from_dict(config_dict)

            if self.is_edit and self.app.state.editing_config_index is not None:
                self.app.state.update_config(self.app.state.editing_config_index, config)
                self.app.notify(f"Updated security {config.isin}", severity="information")
                self.app.state.editing_config_index = None
            else:
                self.app.state.add_config(config)
                self.app.notify(f"Added security {config.isin}", severity="information")

            return True

        except ValidationError as e:
            error_label = self.query_one("#error-message", Label)
            error_label.update(f"Validation Error: {str(e)}")
            self.app.notify("Validation failed", severity="error")
            return False
        except Exception as e:
            error_label = self.query_one("#error-message", Label)
            error_label.update(f"Error: {str(e)}")
            self.app.notify("Error saving config", severity="error")
            return False

    def _gather_form_data(self) -> dict:
        """Gather all form data into a dictionary."""
        isin = self.query_one("#isin", Input).value.strip()
        security_type = self.query_one("#security-type", Select).value
        start_date = self.query_one("#start-date", Input).value.strip()
        end_date = self.query_one("#end-date", Input).value.strip()
        starting_quantity = self.query_one("#starting-quantity", Input).value.strip()
        starting_price = self.query_one("#starting-price", Input).value.strip()

        config_dict = {
            'isin': isin,
            'type': security_type,
            'start_date': start_date,
            'end_date': end_date,
            'starting_quantity': float(starting_quantity) if starting_quantity else 0.0,
            'starting_moving_avg_price': float(starting_price) if starting_price else 0.0,
        }

        # Add OeKB fields if provided
        oekb_date = self.query_one("#oekb-date", Input).value.strip()
        if oekb_date:
            config_dict['oekb_report_date'] = oekb_date

        dei_factor = self.query_one("#dei-factor", Input).value.strip()
        if dei_factor:
            config_dict['oekb_distribution_equivalent_income_factor'] = float(dei_factor)

        tpa_factor = self.query_one("#tpa-factor", Input).value.strip()
        if tpa_factor:
            config_dict['oekb_taxes_paid_abroad_factor'] = float(tpa_factor)

        adj_factor = self.query_one("#adj-factor", Input).value.strip()
        if adj_factor:
            config_dict['oekb_adjustment_factor'] = float(adj_factor)

        currency = self.query_one("#currency", Input).value.strip()
        if currency:
            config_dict['oekb_report_currency'] = currency

        return config_dict
