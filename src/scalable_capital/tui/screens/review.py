"""Review screen for confirming configurations before calculation."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Label, DataTable


class ReviewScreen(Screen):
    """Screen for reviewing configurations before running calculations."""

    BINDINGS = [
        Binding("enter", "calculate", "Calculate"),
        Binding("c", "calculate", "Calculate", show=False),
        Binding("escape", "back", "Back to Edit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the review screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static("[bold]Review & Confirm[/]", classes="header")

                with VerticalScroll():
                    yield Label("\nPlease review your configuration before running the calculation:")

                    yield Label(f"\nTransaction File: {self.app.state.transaction_file}", classes="help-text")
                    yield Label(f"Number of Securities: {len(self.app.state.configs)}", classes="help-text")

                    yield Label("\nConfigured Securities:", classes="help-text")
                    yield DataTable(id="review-table")

                with Horizontal():
                    yield Button("Back to Edit", id="back", variant="default")
                    yield Button("Run Calculation", id="calculate", variant="success")

                yield Static("", classes="footer", id="status")

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        self._setup_table()
        self._populate_table()

    def _setup_table(self) -> None:
        """Setup the DataTable columns."""
        table = self.query_one("#review-table", DataTable)
        table.add_column("ISIN", key="isin")
        table.add_column("Type", key="type")
        table.add_column("Period", key="period")
        table.add_column("Start Qty", key="qty")
        table.add_column("Start Price", key="price")
        table.add_column("OeKB Date", key="oekb")

    def _populate_table(self) -> None:
        """Populate the table with configurations."""
        table = self.query_one("#review-table", DataTable)

        for config in self.app.state.configs:
            period = f"{config.start_date.strftime('%d/%m/%Y')} - {config.end_date.strftime('%d/%m/%Y')}"
            oekb = config.oekb_report_date.strftime('%d/%m/%Y') if config.oekb_report_date else "N/A"

            table.add_row(
                config.isin,
                config.security_type.value,
                period,
                f"{config.starting_quantity:.3f}",
                f"{config.starting_moving_avg_price:.4f}",
                oekb
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "calculate":
            # Move to processing screen
            from scalable_capital.tui.screens.processing import ProcessingScreen
            self.app.push_screen(ProcessingScreen())

    # Keyboard action handlers
    def action_calculate(self) -> None:
        """Run calculation (keyboard shortcut)."""
        from scalable_capital.tui.screens.processing import ProcessingScreen
        self.app.push_screen(ProcessingScreen())

    def action_back(self) -> None:
        """Go back (keyboard shortcut)."""
        self.app.pop_screen()
