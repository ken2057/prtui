"""Navigation mixin for focus cycling between DataTables."""

from __future__ import annotations
from typing import TYPE_CHECKING

from textual.widgets import DataTable, Collapsible
from textual.widgets._collapsible import CollapsibleTitle
from textual.containers import VerticalScroll

if TYPE_CHECKING:
    from textual.app import App as _Base
else:
    _Base = object


class NavigationMixin(_Base):
    """Mixin providing focus cycling between DataTables."""

    def _focused_table(self):
        """Return the DataTable that currently has focus, or the first table."""
        if isinstance(self.focused, DataTable):
            return self.focused
        return self.query(DataTable).first()

    def _cycle_focus(self, direction: int) -> None:
        panel = self.query_one("#comments", VerticalScroll)
        if panel.display:
            collapsibles = list(panel.query(Collapsible))
            if collapsibles:
                # Walk up from focused widget to find parent Collapsible
                current = None
                node = self.focused
                while node is not None:
                    if isinstance(node, Collapsible) and node in collapsibles:
                        current = node
                        break
                    node = node.parent
                if current:
                    idx = collapsibles.index(current)
                    target = collapsibles[(idx + direction) % len(collapsibles)]
                else:
                    target = collapsibles[0 if direction == 1 else -1]
                target.query_one(CollapsibleTitle).focus()
                target.scroll_visible()
                return
        tables = [t for t in self.query(DataTable) if t.display]
        focused = self.focused
        if isinstance(focused, DataTable) and focused in tables:
            idx = tables.index(focused)
            tables[(idx + direction) % len(tables)].focus()
        else:
            tables[0].focus()

    def action_focus_next_table(self) -> None:
        self._cycle_focus(1)

    def action_focus_prev_table(self) -> None:
        self._cycle_focus(-1)
