from __future__ import annotations

"""Explorer selection, expansion, and scrolling synchronization."""

from typing import Any, Callable, Optional


class TreeSyncEngine:
    """Synchronize a tree with the newly opened navigation target."""

    def __init__(self, tree: Any) -> None:
        self.tree = tree
        self._last_parent: Optional[Any] = None

    @staticmethod
    def _expand_ancestors(item: Any) -> None:
        parent = item.parent() if item is not None and hasattr(item, "parent") else None
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

    def sync_item(self, item: Any, *, collapse_previous: bool = True) -> bool:
        if item is None or self.tree is None:
            return False
        parent = item.parent() if hasattr(item, "parent") else None
        current_item = self.tree.currentItem() if hasattr(self.tree, "currentItem") else None
        current_parent = (
            current_item.parent()
            if current_item is not None and hasattr(current_item, "parent")
            else None
        )
        previous_parent = current_parent or self._last_parent
        if collapse_previous and previous_parent is not None and previous_parent is not parent:
            previous_parent.setExpanded(False)
        self._expand_ancestors(item)
        self.tree.blockSignals(True)
        try:
            self.tree.setCurrentItem(item)
        finally:
            self.tree.blockSignals(False)
        self.tree.scrollToItem(item)
        self._last_parent = parent
        return True

    def change_series(
        self,
        target: Any,
        change_handler: Optional[Callable[[Any], None]] = None,
    ) -> bool:
        """Apply heavier synchronization only when a group boundary is crossed."""
        if change_handler is not None:
            # DICOM handlers may receive an integer index and are responsible
            # for resolving it to the corresponding tree item.  Returning
            # False explicitly allows the controller to report a failed sync.
            return change_handler(target) is not False
        return self.sync_item(target, collapse_previous=True)
