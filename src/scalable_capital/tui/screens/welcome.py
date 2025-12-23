"""Welcome screen for the TUI."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Center
from textual.screen import Screen
from textual.widgets import Button, Static, Label
from pathlib import Path


class WelcomeScreen(Screen):
    """Welcome screen with options to start a new configuration or load existing."""

    BINDINGS = [
        Binding("enter", "start", "Get Started"),
        Binding("s", "start", "Start", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the welcome screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static(
                    "[bold cyan]Welcome to Scalable Capital Austrian Tax Calculator[/]",
                    classes="header"
                )

                with Center():
                    with Vertical():
                        yield Label(
                            "\n\n[bold]Calculate taxes for your investments according to Austrian tax law[/]\n\n"
                            "This tool helps you calculate:\n"
                            "  • Distribution equivalent income (Ausschüttungsgleiche Erträge)\n"
                            "  • Foreign taxes paid (Anzurechnende ausländische Quellensteuer)\n"
                            "  • Capital gains from security sales\n\n"
                            "All calculations are based on OeKB reports and ECB exchange rates.\n\n"
                            "[cyan]First, you'll select your transaction file (CSV or JSON),[/]\n"
                            "[cyan]then configure the securities you want to calculate.[/]\n\n"
                            "[yellow]⚠ IMPORTANT:[/] Before running calculations, ensure your ECB exchange rate\n"
                            "data is up to date by running: [bold cyan]rye sync[/]\n"
                            "This updates the currency converter to include the latest exchange rates.\n\n",
                        )

                        with Center():
                            with Vertical():
                                yield Button("Get Started", id="start", variant="primary")
                                yield Button("Quit", id="quit", variant="error")

                yield Static(
                    "Press Ctrl+Q to quit at any time",
                    classes="footer"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "start":
            from scalable_capital.tui.screens.file_selection import FileSelectionScreen
            self.app.push_screen(FileSelectionScreen())
        elif event.button.id == "quit":
            self.app.exit()

    # Keyboard action handlers
    def action_start(self) -> None:
        """Get started (keyboard shortcut)."""
        from scalable_capital.tui.screens.file_selection import FileSelectionScreen
        self.app.push_screen(FileSelectionScreen())

    def action_quit(self) -> None:
        """Quit (keyboard shortcut)."""
        self.app.exit()
