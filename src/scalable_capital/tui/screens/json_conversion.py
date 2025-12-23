"""JSON conversion screen for converting Scalable Capital API JSON to CSV."""
import csv
import os
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Label, DataTable
from textual.worker import Worker, WorkerState

from scalable_capital.json_converter import convert_json_to_csv
from scalable_capital.constants import DEFAULT_FILE_ENCODING, CSV_DELIMITER


class JSONConversionScreen(Screen):
    """Screen for converting JSON to CSV with preview."""

    BINDINGS = [
        Binding("c", "convert", "Convert"),
        Binding("enter", "confirm", "Confirm & Continue"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, json_path: str):
        super().__init__()
        self.json_path = json_path
        self.csv_path = None
        self.conversion_done = False

    def compose(self) -> ComposeResult:
        """Compose the JSON conversion screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static("[bold]JSON Conversion[/]", classes="header")

                with VerticalScroll():
                    yield Label(f"\nJSON file detected: {Path(self.json_path).name}")
                    yield Label("Converting to CSV format for processing...", classes="help-text")
                    yield Label(
                        "\n[yellow]Note:[/] Only [bold]settled security transactions[/] (buy/sell) will be converted.\n"
                        "The following will be [red]excluded[/]:\n"
                        "  • Cash transactions (deposits, withdrawals, fees, interest)\n"
                        "  • Non-trade security transactions (transfers, splits)\n"
                        "  • Non-settled transactions (cancelled, pending orders)",
                        classes="help-text"
                    )

                    yield Static("", id="conversion-status")

                    yield Label("\nPreview of converted CSV:", classes="help-text")
                    yield DataTable(id="preview-table")

                with Horizontal():
                    yield Button("Back", id="back", variant="default")
                    yield Button("Convert", id="convert", variant="primary")
                    yield Button("Confirm & Continue", id="confirm", variant="success", disabled=True)

                yield Static("", classes="footer", id="status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "convert":
            self._start_conversion()
        elif event.button.id == "confirm":
            if self.csv_path:
                self.app.state.transaction_file = self.csv_path
                from scalable_capital.tui.screens.config_manager import ConfigManagerScreen
                self.app.push_screen(ConfigManagerScreen())

    def _start_conversion(self) -> None:
        """Start the JSON to CSV conversion in a worker thread."""
        # Generate output CSV path
        base_name = os.path.splitext(self.json_path)[0]
        self.csv_path = f"{base_name}_converted.csv"

        # Update status
        status = self.query_one("#conversion-status", Static)
        status.update("[yellow]Converting...[/]")

        # Run conversion in worker thread
        self.run_worker(self._convert_json, exclusive=True, thread=True)

    def _convert_json(self) -> int:
        """Worker function to convert JSON to CSV."""
        return convert_json_to_csv(self.json_path, self.csv_path)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.state == WorkerState.SUCCESS:
            num_transactions = event.worker.result
            status = self.query_one("#conversion-status", Static)
            status.update(f"[green]✓ Conversion successful! Converted {num_transactions} transactions[/]")

            # Preview the CSV
            self._preview_csv()

            # Enable confirm button
            confirm_btn = self.query_one("#confirm", Button)
            confirm_btn.disabled = False

            self.conversion_done = True
            self.app.notify(f"Converted {num_transactions} transactions", severity="information")

        elif event.state == WorkerState.ERROR:
            status = self.query_one("#conversion-status", Static)
            status.update(f"[red]✗ Conversion failed: {event.worker.error}[/]")
            self.app.notify("Conversion failed", severity="error")

    def _preview_csv(self) -> None:
        """Preview the converted CSV file."""
        if not self.csv_path or not Path(self.csv_path).exists():
            return

        table = self.query_one("#preview-table", DataTable)
        table.clear(columns=True)

        try:
            with open(self.csv_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
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

            footer = self.query_one("#status", Static)
            footer.update(f"[green]Converted CSV preview: showing all {len(rows)} transactions[/]")

        except Exception as e:
            self.app.notify(f"Error previewing CSV: {str(e)}", severity="error")

    # Keyboard action handlers
    def action_convert(self) -> None:
        """Convert JSON (keyboard shortcut)."""
        if not self.conversion_done:
            self._start_conversion()

    def action_confirm(self) -> None:
        """Confirm and continue (keyboard shortcut)."""
        if self.csv_path and self.conversion_done:
            self.app.state.transaction_file = self.csv_path
            from scalable_capital.tui.screens.config_manager import ConfigManagerScreen
            self.app.push_screen(ConfigManagerScreen())
        else:
            self.app.notify("Please convert the JSON file first", severity="warning")

    def action_back(self) -> None:
        """Go back (keyboard shortcut)."""
        self.app.pop_screen()
