"""Processing screen for running tax calculations."""
from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Center
from textual.screen import Screen
from textual.widgets import Static, Label, LoadingIndicator
from textual.worker import Worker, WorkerState

from scalable_capital.tax_calculator import TaxCalculator
from scalable_capital.models import TaxCalculationResult


class ProcessingScreen(Screen):
    """Screen for processing tax calculations with progress indicator."""

    def compose(self) -> ComposeResult:
        """Compose the processing screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static("[bold]Processing Tax Calculations[/]", classes="header")

                with Center():
                    with Vertical():
                        yield Label("\n\n")
                        yield LoadingIndicator()
                        yield Label("\n")
                        yield Static(
                            "[cyan]Loading transactions...[/]",
                            id="status-message"
                        )
                        yield Label("\n\nThis may take a moment...", classes="help-text")

    def on_mount(self) -> None:
        """Called when screen is mounted - start the calculation."""
        self.run_worker(self._calculate_taxes, exclusive=True, thread=True)

    def _calculate_taxes(self) -> List[TaxCalculationResult]:
        """Worker function to calculate taxes."""
        # Get configs and transaction file from state
        configs = self.app.state.configs
        csv_path = self.app.state.transaction_file

        # Create calculator and run calculations
        calculator = TaxCalculator(configs, csv_path)
        return calculator.calculate_taxes()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        status = self.query_one("#status-message", Static)

        if event.state == WorkerState.RUNNING:
            status.update("[cyan]Calculating taxes...[/]")

        elif event.state == WorkerState.SUCCESS:
            status.update("[green]✓ Calculation complete![/]")
            results = event.worker.result

            # Store results in state
            self.app.state.results = results

            # Navigate to results screen
            from scalable_capital.tui.screens.results import ResultsScreen
            self.app.push_screen(ResultsScreen())

        elif event.state == WorkerState.ERROR:
            error = event.worker.error
            status.update(f"[red]✗ Calculation failed: {str(error)}[/]")
            self.app.notify(f"Calculation error: {str(error)}", severity="error", timeout=10)
