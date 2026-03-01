"""Terminal UI for managing your GitHub pull request inbox."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Collapsible, Markdown, LoadingIndicator
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual.events import DescendantFocus
import threading
import store
import ghapi
from navigation import NavigationMixin

STATE_DISPLAY = {
    "unread": "● new",
    "read": "  read",
    "dismissed": "  —",
}

class GhMail(NavigationMixin, App):
    CSS_PATH = "prtui.tcss"

    TITLE = "prtui"
    SUB_TITLE = "GitHub Pull Request Inbox"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "mark_read", "Mark Read"),
        Binding("d", "dismiss", "Dismiss"),
        Binding("down", "nav_down", "Down", show=False, priority=True),
        Binding("up", "nav_up", "Up", show=False, priority=True),
        Binding("tab", "focus_next_table", "Next Table", show=False, priority=True),
        Binding("shift+tab", "focus_prev_table", "Prev Table", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator()
        yield Horizontal(
            Vertical(
                DataTable(id="prs"),
                DataTable(id="reviewer"),
                DataTable(id="requested"),
            ),
            VerticalScroll(id="comments"),
        )
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._do_fetch()

    def _do_fetch(self) -> None:
        """Fetch PRs in background thread with progress updates."""
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self) -> None:
        try:
            if not store.get_pull_requests("mine"):
                self.call_from_thread(self._show_loading, True)
                ghapi.fetch_and_store(
                    on_progress=lambda msg: self.call_from_thread(
                        self.notify, msg)
                )
                self.call_from_thread(self._show_loading, False)
            self.my_prs = store.get_pull_requests("mine")
            self.review = store.get_pull_requests("reviewer")
            self.requested = store.get_pull_requests("requested")
            self.call_from_thread(self._populate_tables)
        except Exception as e:
            self.call_from_thread(self._show_loading, False)
            self.call_from_thread(self.notify, f"Fetch failed: {e}",
                                  severity="error")

    def _show_loading(self, show: bool) -> None:
        try:
            indicator = self.query_one(LoadingIndicator)
            indicator.display = show
        except Exception:
            pass

    def _populate_tables(self) -> None:
        for table_id, prs in (("#prs", self.my_prs),
                               ("#reviewer", self.review),
                               ("#requested", self.requested)):
            table = self.query_one(table_id, DataTable)
            table.clear(columns=True)
            table.cursor_type = "row"
            table.zebra_stripes = True
            table.add_columns("State", "Repo", "Title", "Author")
            for pr in prs:
                table.add_row(
                    STATE_DISPLAY[pr["state"]],
                    pr["repo"],
                    pr["title"],
                    pr["author"],
                    key=f"{pr['repo']}#{pr['number']}",
                )
        self._update_status()
        first = self.query_one("#prs", DataTable)
        first.focus()
        self.set_timer(0.1, lambda: self._update_comments(first))

    def _focused_table(self):
        """Return the DataTable that currently has focus."""
        if isinstance(self.focused, DataTable):
            return self.focused

    def _prs_for_table(self, table):
        """Return the PR list backing a given table."""
        table_map = {
            "prs": self.my_prs,
            "reviewer": self.review,
            "requested": self.requested,
        }
        return table_map.get(table.id, [])

    def _all_prs(self):
        return self.my_prs + self.review + self.requested

    def _set_state(self, state: str) -> None:
        table = self._focused_table()
        row = table.cursor_row
        prs = self._prs_for_table(table)
        if row >= len(prs):
            return
        prs[row]["state"] = state
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        repo, number = row_key.value.rsplit("#", 1)
        if state == "read":
            store.mark_read(repo, number)
        table.update_cell_at((row, 0), STATE_DISPLAY[state])
        self._update_status()

    def _update_status(self) -> None:
        all_prs = self._all_prs()
        unread = sum(1 for pr in all_prs if pr["state"] == "unread")
        total = len(all_prs)
        self.query_one("#status", Static).update(
            f" {unread} unread / {total} total"
        )

    def action_mark_read(self) -> None:
        self._set_state("read")

    def action_dismiss(self) -> None:
        self._set_state("dismissed")

    def _format_comment(self, comment):
        return Markdown(comment["comment"])

    def _update_comments(self, table: DataTable) -> None:
        if table.row_count == 0:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        repo, number = row_key.value.rsplit("#", 1)
        comments = store.get_comments(repo, number)
        panel = self.query_one("#comments", VerticalScroll)
        panel.remove_children()
        for i, comment in enumerate(comments):
            panel.mount(
                Collapsible(
                    self._format_comment(comment),
                    collapsed=(i != 0),
                    title=comment["user"],
                )
            )

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        self._update_comments(event.data_table)

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        if isinstance(event.widget, DataTable):
            self._update_comments(event.widget)


if __name__ == "__main__":
    GhMail().run()
