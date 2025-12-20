"""Config manager screen for managing securities."""
import csv
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Label, DataTable

from scalable_capital.constants import DEFAULT_FILE_ENCODING, CSV_DELIMITER
from scalable_capital.tui.utils import clean_file_path_input


class ConfigManagerScreen(Screen):
    """Screen for managing security configurations."""

    BINDINGS = [
        Binding("a", "add_security", "Add Security"),
        Binding("e", "edit_security", "Edit Selected"),
        Binding("delete", "delete_security", "Delete Selected"),
        Binding("enter", "edit_security", "Edit", show=False),
        Binding("s", "save_config", "Save Config"),
        Binding("l", "load_config", "Load Config"),
        Binding("r", "review", "Review & Calculate"),
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the config manager screen."""
        with Container(classes="container"):
            with Vertical():
                yield Static("[bold]Manage Securities[/]", classes="header")

                with VerticalScroll():
                    yield Label("\nConfigure the securities you want to calculate taxes for:")
                    yield Label(f"Transaction file: {self.app.state.transaction_file}", classes="help-text")
                    yield Label(
                        "\n[cyan]You can:[/] Add securities manually one-by-one, load from an existing config file, or both!",
                        classes="help-text"
                    )

                    yield Label("\nConfigured Securities:", classes="help-text")
                    yield DataTable(id="config-table", cursor_type="row")

                with Horizontal():
                    yield Button("Back", id="back", variant="default")
                    yield Button("Load Config File", id="load", variant="default")
                    yield Button("Add Security", id="add", variant="primary")
                    yield Button("Edit Selected", id="edit", variant="default", disabled=True)
                    yield Button("Delete Selected", id="delete", variant="error", disabled=True)
                    yield Button("Save Config", id="save", variant="default")
                    yield Button("Review & Calculate", id="review", variant="success")

                yield Static("", classes="footer", id="status")

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        self._setup_table()
        self._refresh_table()
        self._show_available_isins()

    def _setup_table(self) -> None:
        """Setup the DataTable columns."""
        table = self.query_one("#config-table", DataTable)
        table.add_column("ISIN", key="isin")
        table.add_column("Type", key="type")
        table.add_column("Start Date", key="start_date")
        table.add_column("End Date", key="end_date")
        table.add_column("Starting Qty", key="qty")
        table.add_column("Starting Price", key="price")

    def _refresh_table(self) -> None:
        """Refresh the table with current configs."""
        table = self.query_one("#config-table", DataTable)
        table.clear()

        for config in self.app.state.configs:
            table.add_row(
                config.isin,
                config.security_type.value,
                config.start_date.strftime('%d/%m/%Y'),
                config.end_date.strftime('%d/%m/%Y'),
                f"{config.starting_quantity:.3f}",
                f"{config.starting_moving_avg_price:.4f}"
            )

        # Update status
        status = self.query_one("#status", Static)
        status.update(f"{len(self.app.state.configs)} securities configured")

    def _show_available_isins(self) -> None:
        """Show ISINs found in transaction file."""
        if not self.app.state.transaction_file:
            return

        try:
            isins = set()
            with open(self.app.state.transaction_file, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
                reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
                for row in reader:
                    if row.get('isin'):
                        isins.add(row['isin'])

            # Filter out already configured ISINs
            configured_isins = {config.isin for config in self.app.state.configs}
            unconfigured_isins = isins - configured_isins

            if unconfigured_isins:
                self.app.notify(
                    f"Found {len(unconfigured_isins)} ISINs in transaction file: {', '.join(list(unconfigured_isins)[:3])}{'...' if len(unconfigured_isins) > 3 else ''}",
                    severity="information",
                    timeout=10
                )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "load":
            self._load_config()
        elif event.button.id == "add":
            self._add_security()
        elif event.button.id == "edit":
            self._edit_security()
        elif event.button.id == "delete":
            self._delete_security()
        elif event.button.id == "save":
            self._save_config()
        elif event.button.id == "review":
            if not self.app.state.configs:
                self.app.notify("Please add at least one security", severity="warning")
                return
            from scalable_capital.tui.screens.review import ReviewScreen
            self.app.push_screen(ReviewScreen())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        # Enable edit and delete buttons when a row is selected
        edit_btn = self.query_one("#edit", Button)
        delete_btn = self.query_one("#delete", Button)
        edit_btn.disabled = False
        delete_btn.disabled = False

    def _add_security(self) -> None:
        """Add a new security configuration."""
        from scalable_capital.tui.screens.config_form import ConfigFormScreen
        self.app.push_screen(ConfigFormScreen(on_save=self._on_config_saved))

    def _edit_security(self) -> None:
        """Edit the selected security."""
        table = self.query_one("#config-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.app.state.configs):
            from scalable_capital.tui.screens.config_form import ConfigFormScreen
            self.app.state.editing_config_index = table.cursor_row
            config = self.app.state.configs[table.cursor_row]
            self.app.push_screen(ConfigFormScreen(config=config, on_save=self._on_config_saved))

    def _delete_security(self) -> None:
        """Delete the selected security."""
        table = self.query_one("#config-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.app.state.configs):
            config = self.app.state.configs[table.cursor_row]
            self.app.state.remove_config(table.cursor_row)
            self._refresh_table()
            self.app.notify(f"Deleted security {config.isin}", severity="information")

            # Disable edit/delete buttons
            edit_btn = self.query_one("#edit", Button)
            delete_btn = self.query_one("#delete", Button)
            edit_btn.disabled = True
            delete_btn.disabled = True

    def _save_config(self) -> None:
        """Save configurations to a JSON file."""
        if not self.app.state.configs:
            self.app.notify("No configurations to save", severity="warning")
            return

        from textual.widgets import Input

        class SaveConfigDialog(Screen):
            """Dialog for saving config file."""

            def __init__(self):
                super().__init__()
                self._last_value = ""

            def compose(self) -> ComposeResult:
                with Container(classes="container"):
                    with Vertical():
                        yield Static("[bold]Save Configuration[/]", classes="header")
                        yield Label("\nEnter the path to save the configuration:")
                        yield Input(placeholder="config.json", id="save-path", value="config.json")
                        with Horizontal():
                            yield Button("Save", id="save", variant="success")
                            yield Button("Cancel", id="cancel", variant="default")

            def on_mount(self) -> None:
                """Auto-focus and select all text in input field."""
                input_widget = self.query_one("#save-path", Input)
                input_widget.focus()

            def on_input_changed(self, event: Input.Changed) -> None:
                """Clean file path from drag-and-drop."""
                if event.input.id != "save-path":
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
                    input_widget = self.query_one("#save-path", Input)
                    save_path = input_widget.value.strip()
                    if save_path:
                        try:
                            self.app.state.save_to_json(save_path)
                            self.app.notify(f"Configuration saved to {save_path}", severity="information")
                            self.app.pop_screen()
                        except Exception as e:
                            self.app.notify(f"Error saving config: {str(e)}", severity="error")
                elif event.button.id == "cancel":
                    self.app.pop_screen()

        self.app.push_screen(SaveConfigDialog())

    def _load_config(self) -> None:
        """Load securities from a config file."""
        from textual.widgets import Input

        parent_screen = self

        class LoadConfigDialog(Screen):
            """Dialog for loading config file."""

            def __init__(self):
                super().__init__()
                self._last_value = ""

            def compose(self) -> ComposeResult:
                with Container(classes="container"):
                    with Vertical():
                        yield Static("[bold]Load Configuration File[/]", classes="header")
                        yield Label("\nEnter the path to your configuration JSON file:")
                        yield Label("Note: This will ADD securities to your current list (not replace)", classes="help-text")
                        yield Input(placeholder="tax_config.json", id="config-path")
                        with Horizontal():
                            yield Button("Load & Add", id="load", variant="primary")
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
                if event.button.id == "load":
                    input_widget = self.query_one("#config-path", Input)
                    config_path = input_widget.value.strip()
                    if config_path and Path(config_path).exists():
                        try:
                            # Load the config file
                            import json
                            from scalable_capital.constants import DEFAULT_FILE_ENCODING
                            from scalable_capital.models import Config

                            with open(config_path, 'r', encoding=DEFAULT_FILE_ENCODING) as f:
                                config_data = json.load(f)

                            # Add each config to the existing list
                            loaded_count = 0
                            for config_dict in config_data:
                                config = Config.from_dict(config_dict)
                                # Check if ISIN already exists
                                if not self.app.state.get_config_by_isin(config.isin):
                                    self.app.state.add_config(config)
                                    loaded_count += 1
                                else:
                                    self.app.notify(f"Skipped {config.isin} (already configured)", severity="warning")

                            self.app.notify(f"Loaded {loaded_count} securities from config file", severity="information")
                            self.app.pop_screen()
                            # Refresh the parent table
                            parent_screen._refresh_table()
                            parent_screen._show_available_isins()
                        except Exception as e:
                            self.app.notify(f"Error loading config: {str(e)}", severity="error")
                    else:
                        self.app.notify("File not found", severity="error")
                elif event.button.id == "cancel":
                    self.app.pop_screen()

        self.app.push_screen(LoadConfigDialog())

    def _on_config_saved(self) -> None:
        """Callback when a config is saved."""
        self._refresh_table()
        self._show_available_isins()

    # Keyboard action handlers
    def action_add_security(self) -> None:
        """Add a new security (keyboard shortcut)."""
        self._add_security()

    def action_edit_security(self) -> None:
        """Edit selected security (keyboard shortcut)."""
        table = self.query_one("#config-table", DataTable)
        if table.cursor_row is not None:
            self._edit_security()

    def action_delete_security(self) -> None:
        """Delete selected security (keyboard shortcut)."""
        table = self.query_one("#config-table", DataTable)
        if table.cursor_row is not None:
            self._delete_security()

    def action_save_config(self) -> None:
        """Save config (keyboard shortcut)."""
        self._save_config()

    def action_load_config(self) -> None:
        """Load config (keyboard shortcut)."""
        self._load_config()

    def action_review(self) -> None:
        """Go to review screen (keyboard shortcut)."""
        if not self.app.state.configs:
            self.app.notify("Please add at least one security", severity="warning")
            return
        from scalable_capital.tui.screens.review import ReviewScreen
        self.app.push_screen(ReviewScreen())

    def action_back(self) -> None:
        """Go back (keyboard shortcut)."""
        self.app.pop_screen()
