"""Main TUI application for the Austrian tax calculator."""
from textual.app import App, ComposeResult
from textual.binding import Binding

from scalable_capital.tui.state import TUIState


class TaxCalculatorApp(App):
    """Terminal User Interface for the Austrian tax calculator."""

    CSS = """
    Screen {
        overflow: hidden;
    }

    .container {
        width: 100%;
        height: 100%;
        padding: 2;
    }

    .container > Vertical {
        width: 100%;
        height: 100%;
    }

    .header {
        height: auto;
        dock: top;
        content-align: center middle;
        background: $boost;
        color: $text;
        text-style: bold;
        padding: 1;
    }

    .content {
        height: 1fr;
        padding: 1;
    }

    .footer {
        height: auto;
        dock: bottom;
        background: $panel;
        color: $text-muted;
        content-align: center middle;
        padding: 1;
    }

    Center {
        height: 100%;
        width: 100%;
        align: center middle;
    }

    Button {
        margin: 1;
    }

    .primary {
        background: $primary;
    }

    .success {
        background: $success;
    }

    .warning {
        background: $warning;
    }

    .error {
        background: $error;
    }

    /* Ensure vertical containers distribute space properly */
    Vertical {
        height: 100%;
    }

    /* DataTables should fill available space but be scrollable */
    DataTable {
        height: 1fr;
        min-height: 10;
    }

    VerticalScroll {
        height: 1fr;
        overflow-y: auto;
    }

    TabbedContent {
        height: 1fr;
    }

    Horizontal {
        height: auto;
        width: 100%;
    }

    /* Content sections should be scrollable */
    #config-table, #preview-table, #review-table {
        height: 1fr;
        overflow: auto;
    }

    Input {
        margin: 1 0;
    }

    .form-field {
        height: auto;
        margin: 1 0;
    }

    .help-text {
        color: $text-muted;
        margin: 0 0 1 0;
    }

    .error-text {
        color: $error;
        margin: 0 0 1 0;
    }

    Label {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    TITLE = "Scalable Capital Austrian Tax Calculator"
    SUB_TITLE = "Interactive TUI for calculating taxes on investments"

    def __init__(self):
        super().__init__()
        self.state = TUIState()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Import here to avoid circular imports
        from scalable_capital.tui.screens.welcome import WelcomeScreen
        self.push_screen(WelcomeScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
