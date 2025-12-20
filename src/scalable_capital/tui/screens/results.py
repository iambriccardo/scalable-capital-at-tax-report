"""Results screen for displaying tax calculation results."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Label, TabbedContent, TabPane, RichLog

from scalable_capital.models import TaxCalculationResult, AdjustmentTransaction, BuyTransaction, SellTransaction, SecurityType
from scalable_capital.constants import AUSTRIAN_CAPITAL_GAINS_TAX_RATE
from scalable_capital.excel_report import generate_excel_report
from scalable_capital.tui.utils import clean_file_path_input


class ResultsScreen(Screen):
    """Screen for displaying tax calculation results."""

    BINDINGS = [
        Binding("x", "save_excel", "Save Excel"),
        Binding("c", "export_config", "Export Config"),
        Binding("n", "new_calculation", "New Calculation"),
        Binding("q", "exit_app", "Exit"),
        Binding("left", "previous_tab", "Previous Tab", show=False),
        Binding("right", "next_tab", "Next Tab", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the results screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static("[bold]Tax Calculation Results[/]", classes="header")

                yield TabbedContent(id="results-tabs")

                with Horizontal():
                    yield Button("Save Excel Report", id="excel", variant="primary")
                    yield Button("Export Config", id="export-config", variant="default")
                    yield Button("New Calculation", id="new", variant="default")
                    yield Button("Exit", id="exit", variant="error")

                yield Static("", classes="footer", id="status")

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        if not self.app.state.results:
            self.app.notify("No results to display", severity="error")
            self.app.pop_screen()
            return

        self._populate_tabs()

    def _populate_tabs(self) -> None:
        """Populate the tabbed content with results."""
        tabs = self.query_one("#results-tabs", TabbedContent)

        # Add a tab for each security
        for result in self.app.state.results:
            pane = TabPane(result.isin, id=f"tab-{result.isin}")
            tabs.add_pane(pane)
            # Create scroll container, mount it to pane, then populate it
            scroll = VerticalScroll()
            pane.mount(scroll)
            self._populate_security_content(scroll, result)

        # Add summary tab
        summary_pane = TabPane("📊 Summary", id="tab-summary")
        tabs.add_pane(summary_pane)
        # Create scroll container, mount it to pane, then populate it
        scroll = VerticalScroll()
        summary_pane.mount(scroll)
        self._populate_summary_content(scroll)

    def _populate_security_content(self, scroll: VerticalScroll, result: TaxCalculationResult) -> None:
        """Populate a scroll container with content for a single security tab."""
        # Header
        scroll.mount(Label(f"\n[bold white on blue] {result.isin} [/]\n", classes="section-header"))

        # Details section
        scroll.mount(Label("[bold cyan]📋 Security Details[/]"))
        scroll.mount(Label(f"[dim]Type:[/]   [bold]{result.security_type.value.replace('_', ' ').title()}[/]"))
        scroll.mount(Label(f"[dim]Period:[/] [bold]{result.start_date.strftime('%d/%m/%Y')}[/] → [bold]{result.end_date.strftime('%d/%m/%Y')}[/]\n"))

        if result.security_type == SecurityType.ACCUMULATING_ETF and result.report_date:
            scroll.mount(Label("[bold cyan]🏦 OeKB Information[/]"))
            scroll.mount(Label(f"[dim]Report Date:[/]                 [yellow]{result.report_date.strftime('%d/%m/%Y')}[/]"))
            scroll.mount(Label(f"[dim]Distribution Income Factor:[/]  [yellow]{result.distribution_equivalent_income_factor:.4f}[/]"))
            scroll.mount(Label(f"[dim]Taxes Paid Abroad Factor:[/]    [yellow]{result.taxes_paid_abroad_factor:.4f}[/]"))
            scroll.mount(Label(f"[dim]Adjustment Factor:[/]            [yellow]{result.adjustment_factor:.4f}[/]"))
            scroll.mount(Label(f"[dim]ECB Exchange Rate:[/]            [yellow]{result.ecb_exchange_rate:.4f}[/] ({result.report_currency} → EUR)\n"))

        # Transactions
        scroll.mount(Label("[bold cyan]📊 Transaction History[/]"))
        transactions_log = RichLog(wrap=False, markup=True)
        transactions_log.write(f"{'Date':<12} {'Type':<6} {'Qty':>10} {'Price':>12} {'Total':>12} {'Mov.Avg':>12} {'Total Qty':>11}")
        transactions_log.write("─" * 78)

        # Starting row
        transactions_log.write(
            f"[dim]{result.start_date.strftime('%d/%m/%Y'):<12}[/] "
            f"[bold cyan]{'START':<6}[/] "
            f"[yellow]{result.starting_quantity:>10.3f}[/] "
            f"{'—':>12} "
            f"{'—':>12} "
            f"[green]{result.starting_moving_avg_price:>12.4f}[/] "
            f"[magenta]{result.starting_quantity:>11.3f}[/]"
        )

        # Transaction rows
        for trans in result.computed_transactions:
            if isinstance(trans, AdjustmentTransaction):
                # Calculate the adjustment amount properly
                # Total Ertrag in EUR = shares × distribution factor × exchange rate
                adj_total_eur = (result.total_quantity_before_report *
                                result.distribution_equivalent_income_factor *
                                result.ecb_exchange_rate)

                # Adjustment per share = total adjustment / number of shares
                adj_per_share = adj_total_eur / trans.total_quantity if trans.total_quantity > 0 else 0

                # Calculate what the moving average was before this adjustment
                previous_moving_avg = trans.moving_avg_price - adj_per_share

                transactions_log.write(
                    f"[dim]{trans.date.strftime('%d/%m/%Y'):<12}[/] "
                    f"[yellow]{'ADJ':<6}[/] "
                    f"[dim]{0.0:>10.3f}[/] "
                    f"[dim]{0.0:>12.4f}[/] "
                    f"[yellow]+{adj_total_eur:>11.4f}[/] "
                    f"[green]{trans.moving_avg_price:>12.4f}[/] "
                    f"[magenta]{trans.total_quantity:>11.3f}[/]"
                )
                # Add explanatory notes below the adjustment row
                transactions_log.write(
                    f"[dim]{'':12} ├─ Ausschüttungsgleiche Erträge: {result.total_quantity_before_report:.3f} shares × "
                    f"{result.distribution_equivalent_income_factor:.4f} factor × "
                    f"{result.ecb_exchange_rate:.6f} EUR/{result.report_currency} = {adj_total_eur:.4f} EUR[/]"
                )
                transactions_log.write(
                    f"[dim]{'':12} └─ Adjusted Moving Avg: {previous_moving_avg:.4f} + {adj_per_share:.4f} (adjustment/share) = "
                    f"{trans.moving_avg_price:.4f} EUR[/]"
                )
            elif isinstance(trans, BuyTransaction):
                transactions_log.write(
                    f"[dim]{trans.date.strftime('%d/%m/%Y'):<12}[/] "
                    f"[green]{'BUY':<6}[/] "
                    f"[yellow]{trans.quantity:>10.3f}[/] "
                    f"{trans.share_price:>12.3f} "
                    f"{trans.total_price():>12.4f} "
                    f"[green]{trans.moving_avg_price:>12.4f}[/] "
                    f"[magenta]{trans.total_quantity:>11.3f}[/]"
                )
            elif isinstance(trans, SellTransaction):
                transactions_log.write(
                    f"[dim]{trans.date.strftime('%d/%m/%Y'):<12}[/] "
                    f"[red]{'SELL':<6}[/] "
                    f"[yellow]{trans.quantity:>10.3f}[/] "
                    f"{trans.share_price:>12.3f} "
                    f"{trans.total_price():>12.4f} "
                    f"[green]{trans.moving_avg_price:>12.4f}[/] "
                    f"[magenta]{trans.total_quantity:>11.3f}[/]"
                )

        scroll.mount(transactions_log)

        # Tax Summary Box
        dei = round(result.distribution_equivalent_income, 2)
        tpa = round(result.taxes_paid_abroad, 2)
        cg = round(result.total_capital_gains, 2)

        scroll.mount(Label("\n[bold white on green] 💰 TAX SUMMARY [/]\n"))
        scroll.mount(Label(f"[bold cyan]Distribution Equivalent Income[/] [dim](Kennzahl 936/937)[/]"))
        scroll.mount(Label(f"  [bold yellow]{dei:>10.2f} EUR[/]\n"))
        scroll.mount(Label(f"[bold cyan]Taxes Paid Abroad[/] [dim](Kennzahl 984/998)[/]"))
        scroll.mount(Label(f"  [bold yellow]{tpa:>10.2f} EUR[/]\n"))
        scroll.mount(Label(f"[bold cyan]Capital Gains from Sales[/]"))
        scroll.mount(Label(f"  [bold yellow]{cg:>10.2f} EUR[/]\n"))

        # Statistics
        scroll.mount(Label("[bold cyan]📈 Share Statistics[/]"))
        scroll.mount(Label(f"[dim]Starting Shares:[/]                   [yellow]{result.starting_quantity:>12.3f}[/]"))
        if result.security_type == SecurityType.ACCUMULATING_ETF and result.report_date:
            scroll.mount(Label(f"[dim]Shares at OeKB Report Date:[/]        [yellow]{result.total_quantity_before_report:>12.3f}[/] [dim]({result.report_date.strftime('%d/%m/%Y')})[/]"))
        scroll.mount(Label(f"[dim]Final Total Shares:[/]                [yellow]{result.total_quantity:>12.3f}[/]"))
        scroll.mount(Label(f"[dim]Final Moving Average Price:[/]        [yellow]{result.final_moving_avg_price:>12.4f}[/] EUR"))

    def _populate_summary_content(self, scroll: VerticalScroll) -> None:
        """Populate a scroll container with the summary tab content."""
        # Calculate totals
        total_dei = sum(result.distribution_equivalent_income for result in self.app.state.results)
        total_tpa = sum(result.taxes_paid_abroad for result in self.app.state.results)
        total_cg = sum(result.total_capital_gains for result in self.app.state.results)

        dei = round(total_dei, 2)
        tpa = round(total_tpa, 2)
        cg = round(total_cg, 2)
        projected = round(((total_dei + total_cg) * AUSTRIAN_CAPITAL_GAINS_TAX_RATE) - total_tpa, 2)

        # Header
        scroll.mount(Label("\n[bold white on magenta] 📊 FINAL SUMMARY - ALL SECURITIES [/]\n"))

        # Securities breakdown
        scroll.mount(Label("[bold cyan]Securities Breakdown[/]"))
        breakdown_log = RichLog(wrap=False, markup=True)
        breakdown_log.write(f"{'ISIN':<14} {'Type':<18} {'DEI':>11} {'TPA':>11} {'Cap Gains':>14}")
        breakdown_log.write("─" * 78)

        for result in self.app.state.results:
            type_display = result.security_type.value.replace('_', ' ').title()
            breakdown_log.write(
                f"[cyan]{result.isin:<14}[/] "
                f"{type_display:<18} "
                f"[yellow]{round(result.distribution_equivalent_income, 2):>11.2f}[/] "
                f"[yellow]{round(result.taxes_paid_abroad, 2):>11.2f}[/] "
                f"[yellow]{round(result.total_capital_gains, 2):>14.2f}[/]"
            )

        scroll.mount(breakdown_log)

        # Grand Total
        scroll.mount(Label("\n[bold white on blue] 🎯 TOTAL TAX LIABILITY [/]\n"))
        scroll.mount(Label(f"[bold]Distribution Equivalent Income[/] [dim](936/937)[/]  [bold green]{dei:>15.2f} EUR[/]"))
        scroll.mount(Label(f"[bold]Capital Gains[/]                                [bold green]{cg:>15.2f} EUR[/]"))
        scroll.mount(Label(f"[bold]Taxes Paid Abroad[/] [dim](984/998)[/]              [bold red]- {tpa:>13.2f} EUR[/]"))
        scroll.mount(Label("─" * 78))
        scroll.mount(Label(f"[bold white on red] AMOUNT DUE:                             {projected:>15.2f} EUR [/]\n"))

        scroll.mount(Label("[dim]Calculation: (DEI + Capital Gains) × 27.5% - Taxes Paid Abroad[/]"))
        scroll.mount(Label("[dim]All amounts rounded to 2 decimals as required by Finanzonline[/]\n"))

        # Next Steps
        scroll.mount(Label("[bold cyan]📝 Next Steps[/]"))
        scroll.mount(Label("\n[bold]Enter these amounts in your Finanzonline E1kv form:[/]\n"))
        scroll.mount(Label(f"  • Kennzahl [bold]936/937[/]: [yellow]{dei:.2f} EUR[/] [dim](Distribution Equiv. Income)[/]"))
        scroll.mount(Label(f"  • Kennzahl [bold]984/998[/]: [yellow]{tpa:.2f} EUR[/] [dim](Foreign Taxes)[/]"))
        scroll.mount(Label(f"  • [bold]Capital Gains[/]:    [yellow]{cg:.2f} EUR[/]"))
        scroll.mount(Label(f"\n  💶 [bold]Expected tax payment: [yellow]{projected:.2f} EUR[/][/]\n"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "excel":
            self._save_excel_report()
        elif event.button.id == "export-config":
            self._export_config()
        elif event.button.id == "new":
            # Reset state and go back to welcome
            self.app.state.reset()
            self.app.pop_screen()  # Pop results
            self.app.pop_screen()  # Pop processing
            self.app.pop_screen()  # Pop review
            self.app.pop_screen()  # Pop config manager
            self.app.pop_screen()  # Pop file selection
        elif event.button.id == "exit":
            self.app.exit()

    def _save_excel_report(self) -> None:
        """Save Excel report."""
        from textual.widgets import Input

        class ExcelSaveDialog(Screen):
            """Dialog for saving Excel file."""

            def __init__(self):
                super().__init__()
                self._last_value = ""

            def compose(self) -> ComposeResult:
                with Container(classes="container"):
                    with Vertical():
                        yield Static("[bold]Save Excel Report[/]", classes="header")
                        yield Label("\nEnter the path to save the Excel report:")
                        yield Input(placeholder="tax_report.xlsx", id="excel-path", value="tax_report.xlsx")
                        with Horizontal():
                            yield Button("Save", id="save", variant="success")
                            yield Button("Cancel", id="cancel", variant="default")

            def on_mount(self) -> None:
                """Auto-focus the input field."""
                self.query_one("#excel-path", Input).focus()

            def on_input_changed(self, event: Input.Changed) -> None:
                """Clean file path from drag-and-drop."""
                if event.input.id != "excel-path":
                    return
                current = event.value
                if current == self._last_value:
                    return
                cleaned = clean_file_path_input(current)
                if cleaned != current:
                    self._last_value = cleaned
                    event.input.value = cleaned

            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "save":
                    input_widget = self.query_one("#excel-path", Input)
                    excel_path = input_widget.value.strip()
                    if excel_path:
                        try:
                            generate_excel_report(self.app.state.results, excel_path)
                            self.app.notify(f"Excel report saved to {excel_path}", severity="information")
                            self.app.pop_screen()
                        except Exception as e:
                            self.app.notify(f"Error saving Excel: {str(e)}", severity="error")
                elif event.button.id == "cancel":
                    self.app.pop_screen()

        self.app.push_screen(ExcelSaveDialog())

    def _export_config(self) -> None:
        """Export configuration to JSON file."""
        from textual.widgets import Input

        class ConfigExportDialog(Screen):
            """Dialog for exporting config file."""

            def __init__(self):
                super().__init__()
                self._last_value = ""

            def compose(self) -> ComposeResult:
                with Container(classes="container"):
                    with Vertical():
                        yield Static("[bold]Export Configuration[/]", classes="header")
                        yield Label("\nSave the current configuration for future use:")
                        yield Label("You can load this config file later to skip re-entering data", classes="help-text")
                        yield Input(placeholder="tax_config.json", id="config-path", value="tax_config.json")
                        with Horizontal():
                            yield Button("Export", id="export", variant="success")
                            yield Button("Cancel", id="cancel", variant="default")

            def on_mount(self) -> None:
                """Auto-focus the input field."""
                self.query_one("#config-path", Input).focus()

            def on_input_changed(self, event: Input.Changed) -> None:
                """Clean file path from drag-and-drop."""
                if event.input.id != "config-path":
                    return
                current = event.value
                if current == self._last_value:
                    return
                cleaned = clean_file_path_input(current)
                if cleaned != current:
                    self._last_value = cleaned
                    event.input.value = cleaned

            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "export":
                    input_widget = self.query_one("#config-path", Input)
                    config_path = input_widget.value.strip()
                    if config_path:
                        try:
                            self.app.state.save_to_json(config_path)
                            self.app.notify(f"Configuration exported to {config_path}", severity="information")
                            self.app.pop_screen()
                        except Exception as e:
                            self.app.notify(f"Error exporting config: {str(e)}", severity="error")
                elif event.button.id == "cancel":
                    self.app.pop_screen()

        self.app.push_screen(ConfigExportDialog())

    # Keyboard action handlers
    def action_save_excel(self) -> None:
        """Save Excel report (keyboard shortcut)."""
        self._save_excel_report()

    def action_export_config(self) -> None:
        """Export config (keyboard shortcut)."""
        self._export_config()

    def action_new_calculation(self) -> None:
        """Start new calculation (keyboard shortcut)."""
        self.app.state.reset()
        self.app.pop_screen()  # Pop results
        self.app.pop_screen()  # Pop processing
        self.app.pop_screen()  # Pop review
        self.app.pop_screen()  # Pop config manager
        self.app.pop_screen()  # Pop file selection

    def action_exit_app(self) -> None:
        """Exit application (keyboard shortcut)."""
        self.app.exit()

    def action_previous_tab(self) -> None:
        """Navigate to previous tab (keyboard shortcut)."""
        tabs = self.query_one("#results-tabs", TabbedContent)
        current_index = tabs.active_pane_index
        if current_index > 0:
            tabs.active = tabs.tab_ids[current_index - 1]

    def action_next_tab(self) -> None:
        """Navigate to next tab (keyboard shortcut)."""
        tabs = self.query_one("#results-tabs", TabbedContent)
        current_index = tabs.active_pane_index
        if current_index < len(tabs.tab_ids) - 1:
            tabs.active = tabs.tab_ids[current_index + 1]
