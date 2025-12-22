"""Results screen for displaying tax calculation results."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Label, TabbedContent, TabPane, RichLog, DataTable

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
        scroll.mount(Label(f"\n[bold bright_white on dark_blue] 🏦 {result.isin} [/]"))
        scroll.mount(Label(""))

        # Security Details Table
        details_table = DataTable(show_header=False, show_cursor=False)
        details_table.add_column("Property", key="prop", width=25)
        details_table.add_column("Value", key="value", width=50)

        details_table.add_row(
            "[bright_cyan]Security Type[/]",
            f"[bold bright_white]{result.security_type.value.replace('_', ' ').title()}[/]"
        )
        details_table.add_row(
            "[bright_cyan]Reporting Period[/]",
            f"[bold bright_white]{result.start_date.strftime('%d/%m/%Y')}[/] → [bold bright_white]{result.end_date.strftime('%d/%m/%Y')}[/]"
        )

        scroll.mount(details_table)

        # OeKB Information if applicable
        if result.security_type == SecurityType.ACCUMULATING_ETF and result.report_date:
            scroll.mount(Label("\n[bold bright_white on dark_green] 📊 OeKB REPORT DATA [/]"))
            scroll.mount(Label(""))

            oekb_table = DataTable(show_header=False, show_cursor=False)
            oekb_table.add_column("Factor", key="factor", width=40)
            oekb_table.add_column("Value", key="value", width=30)

            oekb_table.add_row(
                "[bright_cyan]Report Date[/]",
                f"[bright_yellow]{result.report_date.strftime('%d/%m/%Y')}[/]"
            )
            oekb_table.add_row(
                "[bright_cyan]Distribution Equivalent Income Factor[/]",
                f"[bright_yellow]{result.distribution_equivalent_income_factor:.6f}[/]"
            )
            oekb_table.add_row(
                "[bright_cyan]Taxes Paid Abroad Factor[/]",
                f"[bright_yellow]{result.taxes_paid_abroad_factor:.6f}[/]"
            )
            oekb_table.add_row(
                "[bright_cyan]Adjustment Factor (per share)[/]",
                f"[bright_yellow]{result.adjustment_factor:.6f}[/]"
            )
            oekb_table.add_row(
                "[bright_cyan]ECB Exchange Rate[/]",
                f"[bright_yellow]{result.ecb_exchange_rate:.6f} {result.report_currency}/EUR[/]"
            )

            scroll.mount(oekb_table)
            scroll.mount(Label(""))

        # Transactions
        scroll.mount(Label("[bold bright_white on purple] 📊 TRANSACTION HISTORY [/]"))
        scroll.mount(Label(""))
        transactions_log = RichLog(wrap=False, markup=True)
        transactions_log.write(f"{'Date':<12} {'Type':<6} {'Qty':>10} {'Price':>12} {'Total':>12} {'Mov.Avg':>12} {'Total Qty':>11}")
        transactions_log.write("─" * 78)

        # Starting row
        transactions_log.write(
            f"[dim]{result.start_date.strftime('%d/%m/%Y'):<12}[/] "
            f"[bold bright_cyan]{'START':<6}[/] "
            f"[bright_yellow]{result.starting_quantity:>10.3f}[/] "
            f"{'—':>12} "
            f"{'—':>12} "
            f"[bright_green]{result.starting_moving_avg_price:>12.4f}[/] "
            f"[bright_magenta]{result.starting_quantity:>11.3f}[/]"
        )

        # Transaction rows
        for trans in result.computed_transactions:
            if isinstance(trans, AdjustmentTransaction):
                # The adjustment_factor is already the per-share adjustment in EUR
                adj_per_share = trans.adjustment_factor

                # Total adjustment applied = adjustment per share × total shares
                adj_total_eur = adj_per_share * trans.total_quantity

                # Ausschüttungsgleiche Erträge (taxable distribution equivalent income)
                # This is different from the adjustment factor - it's the taxable amount
                dei_total = (trans.total_quantity *
                            result.distribution_equivalent_income_factor *
                            result.ecb_exchange_rate)

                # Calculate what the moving average was before this adjustment
                previous_moving_avg = trans.moving_avg_price - adj_per_share

                transactions_log.write(
                    f"[dim]{trans.date.strftime('%d/%m/%Y'):<12}[/] "
                    f"[bright_yellow]{'ADJ':<6}[/] "
                    f"[dim]{0.0:>10.3f}[/] "
                    f"[dim]{0.0:>12.4f}[/] "
                    f"[bright_yellow]+{adj_total_eur:>11.4f}[/] "
                    f"[bright_green]{trans.moving_avg_price:>12.4f}[/] "
                    f"[bright_magenta]{trans.total_quantity:>11.3f}[/]"
                )
                # Add explanatory notes below the adjustment row
                transactions_log.write(
                    f"[dim]{'':12} ├─ Ausschüttungsgleiche Erträge (taxable): {trans.total_quantity:.3f} shares × "
                    f"{result.distribution_equivalent_income_factor:.4f} factor × "
                    f"{result.ecb_exchange_rate:.6f} EUR/{result.report_currency} = {dei_total:.4f} EUR[/]"
                )
                transactions_log.write(
                    f"[dim]{'':12} └─ Adjusted Moving Avg: {previous_moving_avg:.4f} + {adj_per_share:.4f} (adjustment/share) = "
                    f"{trans.moving_avg_price:.4f} EUR[/]"
                )
            elif isinstance(trans, BuyTransaction):
                transactions_log.write(
                    f"[dim]{trans.date.strftime('%d/%m/%Y'):<12}[/] "
                    f"[bright_green]{'BUY':<6}[/] "
                    f"[bright_yellow]{trans.quantity:>10.3f}[/] "
                    f"{trans.share_price:>12.3f} "
                    f"{trans.total_price():>12.4f} "
                    f"[bright_green]{trans.moving_avg_price:>12.4f}[/] "
                    f"[bright_magenta]{trans.total_quantity:>11.3f}[/]"
                )
            elif isinstance(trans, SellTransaction):
                transactions_log.write(
                    f"[dim]{trans.date.strftime('%d/%m/%Y'):<12}[/] "
                    f"[bright_red]{'SELL':<6}[/] "
                    f"[bright_yellow]{trans.quantity:>10.3f}[/] "
                    f"{trans.share_price:>12.3f} "
                    f"{trans.total_price():>12.4f} "
                    f"[bright_green]{trans.moving_avg_price:>12.4f}[/] "
                    f"[bright_magenta]{trans.total_quantity:>11.3f}[/]"
                )

        scroll.mount(transactions_log)

        # Tax Summary Section
        dei = round(result.distribution_equivalent_income, 2)
        tpa = round(result.taxes_paid_abroad, 2)
        cg = round(result.total_capital_gains, 2)
        total_taxable = dei + cg
        estimated_tax = round((total_taxable * AUSTRIAN_CAPITAL_GAINS_TAX_RATE) - tpa, 2)

        scroll.mount(Label("\n"))
        scroll.mount(Label("[bold bright_white on dark_blue] 💰 STEUERÜBERSICHT / TAX SUMMARY [/]"))
        scroll.mount(Label(""))

        # Create tax summary table
        tax_table = DataTable(show_header=True, show_cursor=False)
        tax_table.add_column("Steuerposition / Tax Item", key="item", width=45)
        tax_table.add_column("Kennzahl", key="kennzahl", width=12)
        tax_table.add_column("Betrag (EUR)", key="amount", width=15)

        tax_table.add_row(
            "[bright_cyan]Ausschüttungsgleiche Erträge[/]\n[dim]Distribution-Equivalent Income[/]",
            "[dim]936/937[/]",
            f"[bold bright_yellow]{dei:>12.2f}[/]"
        )
        tax_table.add_row(
            "[bright_cyan]Anrechenbare ausl. Quellensteuer[/]\n[dim]Creditable Foreign Withholding Tax[/]",
            "[dim]984/998[/]",
            f"[bold bright_yellow]{tpa:>12.2f}[/]"
        )
        tax_table.add_row(
            "[bright_cyan]Veräußerungsgewinne[/]\n[dim]Realized Capital Gains[/]",
            "[dim]—[/]",
            f"[bold bright_yellow]{cg:>12.2f}[/]"
        )
        tax_table.add_row(
            "",
            "",
            ""
        )
        tax_table.add_row(
            "[bold bright_green]Bemessungsgrundlage[/]\n[dim]Tax Base (DEI + Capital Gains)[/]",
            "[dim]—[/]",
            f"[bold bright_green]{total_taxable:>12.2f}[/]"
        )
        tax_table.add_row(
            "[bold bright_magenta]Geschätzte KESt (27,5%)[/]\n[dim]Estimated Capital Gains Tax[/]",
            "[dim]—[/]",
            f"[bold bright_magenta]{estimated_tax:>12.2f}[/]"
        )

        scroll.mount(tax_table)

        # Share Statistics Section
        scroll.mount(Label("\n"))
        scroll.mount(Label("[bold bright_white on dark_cyan] 📈 SHARE STATISTICS [/]"))
        scroll.mount(Label(""))

        stats_table = DataTable(show_header=False, show_cursor=False)
        stats_table.add_column("Metric", key="metric", width=40)
        stats_table.add_column("Value", key="value", width=20)

        stats_table.add_row(
            "[bright_cyan]Starting Shares[/]",
            f"[bright_yellow]{result.starting_quantity:>12.3f}[/]"
        )

        if result.security_type == SecurityType.ACCUMULATING_ETF and result.report_date:
            stats_table.add_row(
                f"[bright_cyan]Shares at OeKB Report Date[/] [dim]({result.report_date.strftime('%d/%m/%Y')})[/]",
                f"[bright_yellow]{result.total_quantity_before_report:>12.3f}[/]"
            )

        stats_table.add_row(
            "[bright_cyan]Final Total Shares[/]",
            f"[bright_yellow]{result.total_quantity:>12.3f}[/]"
        )
        stats_table.add_row(
            "[bright_cyan]Starting Moving Avg Price[/]",
            f"[bright_yellow]{result.starting_moving_avg_price:>12.4f} EUR[/]"
        )
        stats_table.add_row(
            "[bright_cyan]Final Moving Avg Price[/]",
            f"[bright_yellow]{result.final_moving_avg_price:>12.4f} EUR[/]"
        )

        scroll.mount(stats_table)
        scroll.mount(Label(""))

    def _populate_summary_content(self, scroll: VerticalScroll) -> None:
        """Populate a scroll container with the summary tab content."""
        # Calculate totals
        total_dei = sum(result.distribution_equivalent_income for result in self.app.state.results)
        total_tpa = sum(result.taxes_paid_abroad for result in self.app.state.results)
        total_cg = sum(result.total_capital_gains for result in self.app.state.results)

        dei = round(total_dei, 2)
        tpa = round(total_tpa, 2)
        cg = round(total_cg, 2)
        total_taxable = dei + cg
        projected = round((total_taxable * AUSTRIAN_CAPITAL_GAINS_TAX_RATE) - tpa, 2)

        # Header
        scroll.mount(Label("\n[bold bright_white on purple] 📊 FINAL SUMMARY - ALL SECURITIES [/]"))
        scroll.mount(Label(""))

        # Key metrics card
        scroll.mount(Label("[bold bright_white on dark_red] 💰 ESTIMATED TAX LIABILITY [/]"))
        scroll.mount(Label(""))

        liability_table = DataTable(show_header=False, show_cursor=False)
        liability_table.add_column("Item", key="item", width=50)
        liability_table.add_column("Amount", key="amount", width=18)

        liability_table.add_row(
            "[bold bright_white]Total Tax Due (estimated)[/]",
            f"[bold bright_white on dark_red] {projected:>12.2f} EUR [/]"
        )
        liability_table.add_row(
            "[dim]From {0} securities[/]".format(len(self.app.state.results)),
            ""
        )

        scroll.mount(liability_table)

        # Securities breakdown
        scroll.mount(Label("\n"))
        scroll.mount(Label("[bold bright_white on dark_blue] 📋 SECURITIES BREAKDOWN [/]"))
        scroll.mount(Label(""))

        breakdown_table = DataTable(show_header=True, show_cursor=False)
        breakdown_table.add_column("ISIN", key="isin", width=14)
        breakdown_table.add_column("Type", key="type", width=20)
        breakdown_table.add_column("DEI (EUR)", key="dei", width=14)
        breakdown_table.add_column("TPA (EUR)", key="tpa", width=14)
        breakdown_table.add_column("Cap Gains (EUR)", key="cg", width=16)

        for result in self.app.state.results:
            type_display = result.security_type.value.replace('_', ' ').title()
            breakdown_table.add_row(
                f"[bright_cyan]{result.isin}[/]",
                type_display,
                f"[bright_yellow]{round(result.distribution_equivalent_income, 2):>12.2f}[/]",
                f"[bright_yellow]{round(result.taxes_paid_abroad, 2):>12.2f}[/]",
                f"[bright_yellow]{round(result.total_capital_gains, 2):>14.2f}[/]"
            )

        scroll.mount(breakdown_table)

        # Grand Total
        scroll.mount(Label("\n"))
        scroll.mount(Label("[bold bright_white on dark_green] 🎯 AGGREGATED TAX CALCULATION [/]"))
        scroll.mount(Label(""))

        total_table = DataTable(show_header=True, show_cursor=False)
        total_table.add_column("Steuerposition / Tax Item", key="item", width=45)
        total_table.add_column("Kennzahl", key="kennzahl", width=12)
        total_table.add_column("Betrag (EUR)", key="amount", width=15)

        total_table.add_row(
            "[bright_cyan]Ausschüttungsgleiche Erträge[/]\n[dim]Distribution-Equivalent Income[/]",
            "[dim]936/937[/]",
            f"[bold bright_yellow]{dei:>12.2f}[/]"
        )
        total_table.add_row(
            "[bright_cyan]Veräußerungsgewinne[/]\n[dim]Realized Capital Gains[/]",
            "[dim]—[/]",
            f"[bold bright_yellow]{cg:>12.2f}[/]"
        )
        total_table.add_row(
            "[bright_cyan]Anrechenbare ausl. Quellensteuer[/]\n[dim]Creditable Foreign Withholding Tax[/]",
            "[dim]984/998[/]",
            f"[bold bright_yellow]{tpa:>12.2f}[/]"
        )
        total_table.add_row("", "", "")
        total_table.add_row(
            "[bold bright_green]Bemessungsgrundlage[/]\n[dim]Tax Base (Total)[/]",
            "[dim]—[/]",
            f"[bold bright_green]{total_taxable:>12.2f}[/]"
        )
        total_table.add_row(
            "[bold bright_magenta]Geschätzte KESt (27,5%)[/]\n[dim]Estimated Capital Gains Tax[/]",
            "[dim]—[/]",
            f"[bold bright_magenta]{projected:>12.2f}[/]"
        )

        scroll.mount(total_table)

        scroll.mount(Label("\n[dim]Berechnung / Calculation: (Ausschüttungsgl. Erträge + Veräußerungsgewinne) × 27,5% - ausl. Quellensteuer[/]"))
        scroll.mount(Label("[dim]All amounts rounded to 2 decimals as required by FinanzOnline[/]\n"))

        # Next Steps
        scroll.mount(Label("\n"))
        scroll.mount(Label("[bold black on bright_yellow] 📝 FINANZONLINE ENTRY GUIDE [/]"))
        scroll.mount(Label(""))

        scroll.mount(Label("[bold bright_white]Enter these amounts in your FinanzOnline E1kv form:[/]\n"))

        finanzonline_table = DataTable(show_header=True, show_cursor=False)
        finanzonline_table.add_column("Kennzahl", key="kennzahl", width=15)
        finanzonline_table.add_column("Bezeichnung / Description", key="desc", width=50)
        finanzonline_table.add_column("Betrag (EUR)", key="amount", width=15)

        finanzonline_table.add_row(
            "[bold bright_white]936/937[/]",
            "Ausschüttungsgleiche Erträge / Distribution-Equivalent Income",
            f"[bright_yellow]{dei:>12.2f}[/]"
        )
        finanzonline_table.add_row(
            "[bold bright_white]984/998[/]",
            "Anrechenbare ausl. Quellensteuer / Creditable Foreign Tax",
            f"[bright_yellow]{tpa:>12.2f}[/]"
        )
        finanzonline_table.add_row(
            "[bold bright_white]—[/]",
            "Veräußerungsgewinne / Realized Capital Gains",
            f"[bright_yellow]{cg:>12.2f}[/]"
        )

        scroll.mount(finanzonline_table)
        scroll.mount(Label(f"\n💶 [bold bright_white on dark_red] VORAUSSICHTLICHE STEUERZAHLUNG / EXPECTED TAX PAYMENT: {projected:>10.2f} EUR [/]\n"))

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
                self._escape_count = 0

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

            def on_key(self, event) -> None:
                """Handle key presses for double-escape to clear input."""
                if event.key == "escape":
                    focused = self.focused
                    if focused and isinstance(focused, Input):
                        self._escape_count += 1
                        if self._escape_count >= 2:
                            focused.value = ""
                            self._escape_count = 0
                            event.prevent_default()
                            event.stop()
                        else:
                            self.set_timer(1.0, lambda: setattr(self, '_escape_count', 0))
                else:
                    self._escape_count = 0

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
                self._escape_count = 0

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

            def on_key(self, event) -> None:
                """Handle key presses for double-escape to clear input."""
                if event.key == "escape":
                    focused = self.focused
                    if focused and isinstance(focused, Input):
                        self._escape_count += 1
                        if self._escape_count >= 2:
                            focused.value = ""
                            self._escape_count = 0
                            event.prevent_default()
                            event.stop()
                        else:
                            self.set_timer(1.0, lambda: setattr(self, '_escape_count', 0))
                else:
                    self._escape_count = 0

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
