"""File selection screen for choosing transaction file."""
import csv
import json
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Label, Input, DataTable

from scalable_capital.constants import DEFAULT_FILE_ENCODING, CSV_DELIMITER
from scalable_capital.tui.utils import clean_file_path_input


class FileSelectionScreen(Screen):
    """Screen for selecting the transaction file (CSV or JSON)."""

    BINDINGS = [
        Binding("p", "preview", "Preview File"),
        Binding("enter", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self._last_value = ""

    def compose(self) -> ComposeResult:
        """Compose the file selection screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static("[bold]Select Transaction File[/]", classes="header")

                with VerticalScroll():
                    yield Label("\nEnter the path to your Scalable Capital transaction file:")
                    yield Label("Supported formats: CSV (direct export) or JSON (API response)", classes="help-text")
                    yield Input(placeholder="transactions.csv or transactions.json", id="file-path")

                    yield Label("\nPreview:", classes="help-text")
                    yield DataTable(id="preview-table")

                with Horizontal():
                    yield Button("Back", id="back", variant="default")
                    yield Button("Load & Preview", id="preview", variant="primary")
                    yield Button("Next", id="next", variant="success")

                yield Static("", classes="footer", id="status")

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        # Auto-focus the input field so drag-and-drop works immediately
        input_widget = self.query_one("#file-path", Input)
        input_widget.focus()

        # Pre-fill if transaction file is already set
        if self.app.state.transaction_file:
            input_widget.value = self.app.state.transaction_file
            self._preview_file(self.app.state.transaction_file)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to clean up file paths from drag-and-drop."""
        if event.input.id != "file-path":
            return

        current = event.value

        # Prevent infinite loops - if we just set this value, don't process it again
        if current == self._last_value:
            return

        # Clean the file path using the utility function
        cleaned = clean_file_path_input(current)

        # Only update if we actually changed something
        if cleaned != current:
            self._last_value = cleaned
            event.input.value = cleaned

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "preview":
            input_widget = self.query_one("#file-path", Input)
            file_path = input_widget.value.strip()
            if file_path:
                self._preview_file(file_path)
        elif event.button.id == "next":
            input_widget = self.query_one("#file-path", Input)
            file_path = input_widget.value.strip()
            if not file_path:
                self.app.notify("Please enter a file path", severity="error")
                return

            if not Path(file_path).exists():
                self.app.notify("File not found", severity="error")
                return

            # Check if it's a JSON file
            if self._is_json_file(file_path):
                from scalable_capital.tui.screens.json_conversion import JSONConversionScreen
                self.app.push_screen(JSONConversionScreen(file_path))
            else:
                # It's a CSV file, go directly to config manager
                self.app.state.transaction_file = file_path
                from scalable_capital.tui.screens.config_manager import ConfigManagerScreen
                self.app.push_screen(ConfigManagerScreen())

    def _is_json_file(self, file_path: str) -> bool:
        """Check if file is a JSON file."""
        if file_path.lower().endswith('.json'):
            return True
        try:
            with open(file_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False

    def _preview_file(self, file_path: str) -> None:
        """Preview the file content in a DataTable."""
        if not Path(file_path).exists():
            self.app.notify("File not found", severity="error")
            return

        table = self.query_one("#preview-table", DataTable)
        table.clear(columns=True)

        try:
            if self._is_json_file(file_path):
                self._preview_json(file_path, table)
            else:
                self._preview_csv(file_path, table)

            status = self.query_one("#status", Static)
            status.update(f"Preview loaded: {Path(file_path).name}")
            self.app.notify("File preview loaded successfully", severity="information")
        except Exception as e:
            self.app.notify(f"Error previewing file: {str(e)}", severity="error")

    def _preview_csv(self, file_path: str, table: DataTable) -> None:
        """Preview a CSV file."""
        with open(file_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            rows = list(reader)

            if not rows:
                return

            # Add columns
            headers = list(rows[0].keys())
            for header in headers:
                table.add_column(header, key=header)

            # Add all rows
            for row in rows:
                table.add_row(*[row[h] for h in headers])

            # Update status with count
            status = self.query_one("#status", Static)
            status.update(f"Showing all {len(rows)} transactions from CSV file")

    def _preview_json(self, file_path: str, table: DataTable) -> None:
        """Preview a JSON file."""
        with open(file_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
            data = json.load(f)

        # Extract transactions from nested structure
        try:
            transactions = data[0]['data']['account']['brokerPortfolio']['moreTransactions']['transactions']
        except (KeyError, IndexError):
            self.app.notify("Invalid JSON structure", severity="error")
            return

        if not transactions:
            return

        # Add columns based on first transaction
        table.add_column("Date", key="date")
        table.add_column("Type", key="type")
        table.add_column("ISIN", key="isin")
        table.add_column("Description", key="description")
        table.add_column("Amount", key="amount")
        table.add_column("Status", key="status")
        table.add_column("Will Be Used", key="used")

        # Count transactions by type
        total_count = len(transactions)
        security_settled = 0
        security_other = 0
        cash_tx = 0
        non_trade = 0

        # Add all rows with indicators
        for tx in transactions:
            tx_type = tx.get('type', 'N/A')
            tx_status = tx.get('status', 'N/A')

            # Determine if this transaction will be used
            will_be_used = "✓ Yes"
            if tx_type == 'SECURITY_TRANSACTION' and tx_status == 'SETTLED':
                will_be_used = "[green]✓ Yes[/]"
                security_settled += 1
            elif tx_type == 'SECURITY_TRANSACTION':
                will_be_used = "[red]✗ No (Not settled)[/]"
                security_other += 1
            elif tx_type == 'CASH_TRANSACTION':
                will_be_used = "[red]✗ No (Cash)[/]"
                cash_tx += 1
            elif tx_type == 'NON_TRADE_SECURITY_TRANSACTION':
                will_be_used = "[red]✗ No (Non-trade)[/]"
                non_trade += 1
            else:
                will_be_used = "[red]✗ No (Unknown)[/]"

            # Extract date
            date_str = tx.get('lastEventDateTime', 'N/A')
            if date_str != 'N/A':
                date_str = date_str.split('T')[0]

            table.add_row(
                date_str,
                tx_type,
                tx.get('isin', 'N/A'),
                tx.get('description', 'N/A')[:40],
                str(tx.get('amount', 'N/A')),
                tx_status,
                will_be_used
            )

        # Update status with detailed count
        status = self.query_one("#status", Static)
        status_message = (
            f"JSON Preview: {total_count} total transactions\n"
            f"[green]✓ {security_settled} settled security transactions (will be converted)[/]\n"
            f"[red]✗ {security_other} non-settled security transactions (skipped)[/]\n"
            f"[red]✗ {cash_tx} cash transactions (skipped)[/]\n"
            f"[red]✗ {non_trade} non-trade transactions (skipped)[/]"
        )
        status.update(status_message)

    # Keyboard action handlers
    def action_preview(self) -> None:
        """Preview file (keyboard shortcut)."""
        input_widget = self.query_one("#file-path", Input)
        file_path = input_widget.value.strip()
        if file_path:
            self._preview_file(file_path)

    def action_next(self) -> None:
        """Go to next screen (keyboard shortcut)."""
        input_widget = self.query_one("#file-path", Input)
        file_path = input_widget.value.strip()
        if not file_path:
            self.app.notify("Please enter a file path", severity="error")
            return

        if not Path(file_path).exists():
            self.app.notify("File not found", severity="error")
            return

        # Check if it's a JSON file
        if self._is_json_file(file_path):
            from scalable_capital.tui.screens.json_conversion import JSONConversionScreen
            self.app.push_screen(JSONConversionScreen(file_path))
        else:
            # It's a CSV file, go directly to config manager
            self.app.state.transaction_file = file_path
            from scalable_capital.tui.screens.config_manager import ConfigManagerScreen
            self.app.push_screen(ConfigManagerScreen())

    def action_back(self) -> None:
        """Go back (keyboard shortcut)."""
        self.app.pop_screen()
