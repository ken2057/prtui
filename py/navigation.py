"""Navigation mixin for panel focus cycling and arrow key handling."""

from textual.widgets import DataTable
from textual.containers import VerticalScroll


class NavigationMixin:
    """Mixin providing focus cycling between DataTables and comments panel."""

    def _is_in_comments(self) -> bool:
        panel = self.query_one("#comments", VerticalScroll)
        focused = self.focused
        return focused is not None and panel in focused.ancestors_with_self

    def _nav_comments(self, direction: int) -> None:
        panel = self.query_one("#comments", VerticalScroll)
        focusable = [w for w in panel.walk_children() if w.can_focus]
        if not focusable:
            return
        focused = self.focused
        if focused in focusable:
            idx = focusable.index(focused)
            new_idx = max(0, min(len(focusable) - 1, idx + direction))
            focusable[new_idx].focus()
        else:
            focusable[0].focus()

    def action_nav_down(self) -> None:
        if self._is_in_comments():
            self._nav_comments(1)
        elif isinstance(self.focused, DataTable):
            self.focused.action_cursor_down()

    def action_nav_up(self) -> None:
        if self._is_in_comments():
            self._nav_comments(-1)
        elif isinstance(self.focused, DataTable):
            self.focused.action_cursor_up()

    def _focus_widget(self, widget) -> None:
        if isinstance(widget, VerticalScroll):
            focusable = [w for w in widget.walk_children() if w.can_focus]
            if focusable:
                focusable[0].focus()
                return
        widget.focus()

    def _cycle_focus(self, direction: int) -> None:
        tables = list(self.query(DataTable)) + [
            self.query_one("#comments", VerticalScroll)
        ]
        focused = self.focused
        panel = self.query_one("#comments", VerticalScroll)
        if focused not in tables and panel in focused.ancestors_with_self:
            focused = panel
        if focused in tables:
            idx = tables.index(focused)
            self._focus_widget(tables[(idx + direction) % len(tables)])
        else:
            self._focus_widget(tables[0])

    def action_focus_next_table(self) -> None:
        self._cycle_focus(1)

    def action_focus_prev_table(self) -> None:
        self._cycle_focus(-1)
