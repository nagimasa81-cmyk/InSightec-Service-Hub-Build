from __future__ import annotations

"""Central navigation coordination for MR Image Explorer."""

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTreeWidgetItemIterator

from core.dicom_provider import DicomNavigationProvider
from core.raw_provider import ExplorerNavigationProvider
from core.tree_sync import TreeSyncEngine


class NavigationController:
    """Coordinate DICOM and Explorer navigation without duplicating order logic."""

    EXPLORER_LEAF_TYPES = {
        "raw_file",
        "bitmap_pending",
        "tracker_file",
        "tracker_pending",
    }

    def __init__(self, window: Any):
        self.window = window
        self.tree_sync = TreeSyncEngine(getattr(window, "tree", None))

    def _dicom_tree_series_groups(self) -> list[tuple[Any, list[int]]]:
        """Return the current Study series exactly as displayed in Explorer.

        Metadata-derived grouping proved unreliable for exported datasets where
        SeriesInstanceUID/description fields are reused or inconsistent.  The
        Explorer tree is the authoritative UI structure, so navigation follows
        its Exam -> Series -> image order directly.
        """
        tree = getattr(self.window, "tree", None)
        if tree is None:
            return []

        current_index = int(getattr(self.window, "slice_index", 0))
        current_leaf = None
        iterator = QTreeWidgetItemIterator(tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if data and data[0] == "dicom" and int(data[1]) == current_index:
                current_leaf = item
                break
            iterator += 1
        if current_leaf is None:
            return []

        current_series = current_leaf.parent()
        current_exam = current_series.parent() if current_series is not None else None
        if current_exam is None:
            return []

        groups: list[tuple[Any, list[int]]] = []
        for series_pos in range(current_exam.childCount()):
            series_item = current_exam.child(series_pos)
            series_data = series_item.data(0, Qt.UserRole)
            if not series_data or series_data[0] != "series":
                continue
            indices: list[int] = []
            for image_pos in range(series_item.childCount()):
                image_item = series_item.child(image_pos)
                image_data = image_item.data(0, Qt.UserRole)
                if image_data and image_data[0] == "dicom":
                    indices.append(int(image_data[1]))
            if indices:
                groups.append((series_data[1], indices))
        return groups

    def _dicom_provider(self) -> DicomNavigationProvider:
        w = self.window
        return DicomNavigationProvider(
            groups_factory=self._dicom_tree_series_groups,
            current_index=lambda: int(getattr(w, "slice_index", 0)),
        )

    def _active_explorer_kind(self) -> str | None:
        """Resolve the leaf type that belongs to the currently displayed source."""
        source_kind = str(getattr(self.window, "source_kind", "") or "")
        if source_kind == "raw_file":
            return "raw_file"
        if source_kind == "bitmap":
            return "bitmap_pending"
        if source_kind.startswith("tracker"):
            return "tracker_file"
        tree = getattr(self.window, "tree", None)
        item = tree.currentItem() if tree is not None else None
        data = item.data(0, Qt.UserRole) if item is not None else None
        return str(data[0]) if data and data[0] in self.EXPLORER_LEAF_TYPES else None

    def _current_explorer_item(self) -> Any:
        """Return the leaf representing the displayed file, even after UI focus changes."""
        tree = getattr(self.window, "tree", None)
        if tree is None:
            return None
        expected_kind = self._active_explorer_kind()
        current = tree.currentItem()
        current_data = current.data(0, Qt.UserRole) if current is not None else None
        if current_data and current_data[0] == expected_kind:
            return current

        current_source = str(getattr(self.window, "current_source", "") or "")
        iterator = QTreeWidgetItemIterator(tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if data and data[0] == expected_kind:
                value = str(data[1]) if len(data) > 1 else ""
                if current_source and value == current_source:
                    return item
            iterator += 1
        return None

    def _explorer_items(self) -> list[Any]:
        """Return only leaves of the active source type in visible tree order."""
        tree = getattr(self.window, "tree", None)
        expected_kind = self._active_explorer_kind()
        if tree is None or expected_kind is None:
            return []
        items: list[Any] = []
        iterator = QTreeWidgetItemIterator(tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if data and data[0] == expected_kind:
                items.append(item)
            iterator += 1
        return items

    def _explorer_provider(self) -> ExplorerNavigationProvider:
        return ExplorerNavigationProvider(
            items_factory=self._explorer_items,
            current_item=self._current_explorer_item,
        )


    def _raw_boundary_target(self, delta: int) -> tuple[Any, bool] | tuple[None, bool]:
        """Resolve RAW navigation from the actual Explorer folder hierarchy.

        This intentionally does not flatten QTreeWidgetItemIterator output.
        The currently displayed RAW leaf is located first, then navigation is
        performed inside its parent folder.  Crossing an edge selects the
        first/last RAW leaf of the adjacent RAW folder, even when that folder
        is collapsed.
        """
        current = self._current_explorer_item()
        if current is None:
            return None, False
        data = current.data(0, Qt.UserRole)
        if not data or data[0] != "raw_file":
            return None, False

        folder = current.parent()
        root = folder.parent() if folder is not None else None
        if folder is None or root is None:
            return None, False

        def raw_children(group: Any) -> list[Any]:
            result: list[Any] = []
            for index in range(group.childCount()):
                child = group.child(index)
                child_data = child.data(0, Qt.UserRole)
                if child_data and child_data[0] == "raw_file":
                    result.append(child)
            return result

        current_items = raw_children(folder)
        if current not in current_items:
            return None, False

        step = -1 if int(delta) < 0 else 1
        position = current_items.index(current)
        next_position = position + step
        if 0 <= next_position < len(current_items):
            return current_items[next_position], False

        try:
            folder_position = root.indexOfChild(folder)
        except Exception:
            folder_position = -1
        if folder_position < 0:
            return None, False

        candidate_position = folder_position + step
        while 0 <= candidate_position < root.childCount():
            candidate_folder = root.child(candidate_position)
            candidate_items = raw_children(candidate_folder)
            if candidate_items:
                return (candidate_items[-1] if step < 0 else candidate_items[0]), True
            candidate_position += step
        return None, False

    def navigate_series(self, delta: int) -> bool:
        """Move within the current DICOM series without crossing a boundary."""
        w = self.window
        if not getattr(w, "dicom_entries", None):
            self.update_ui()
            return False
        indices = w._current_series_indices()
        current = int(getattr(w, "slice_index", 0))
        if not indices:
            self.update_ui()
            return False
        try:
            position = indices.index(current)
        except ValueError:
            position = 0
        target_position = max(0, min(position + (-1 if int(delta) < 0 else 1), len(indices) - 1))
        target_index = indices[target_position]
        if target_index == current:
            self.update_ui()
            return False
        mode = getattr(w, "view_mode", "Both")
        w.show_dicom(target_index)
        if getattr(w, "view_mode", mode) != mode:
            w.set_view_mode(mode)
        return True

    def navigate_continuous(self, delta: int) -> bool:
        """Move in display order across DICOM series or Explorer groups."""
        w = self.window
        step = -1 if int(delta) < 0 else 1

        if getattr(w, "source_kind", None) == "dicom" and getattr(w, "dicom_entries", None):
            provider = self._dicom_provider()
            current = provider.current()
            result = provider.previous() if step < 0 else provider.next()
            if current is None or result is None or result.current_item == current.item:
                self.update_ui()
                return False
            mode = getattr(w, "view_mode", "Both")
            # Expand the destination series and collapse the previous series
            # before loading.  show_dicom() synchronizes the current tree item;
            # doing this first guarantees the destination leaf is visible.
            if result.series_changed:
                self.tree_sync.change_series(
                    result.current_item,
                    getattr(w, "_set_tree_series_expansion_for_index", None),
                )
            w.show_dicom(result.current_item)
            if result.series_changed:
                # show_dicom() performs its own tree selection and Qt may defer
                # layout updates.  Re-apply expansion immediately and once on
                # the next event-loop turn so the destination branch remains
                # visibly open in the built EXE as well as debug mode.
                expansion_handler = getattr(w, "_set_tree_series_expansion_for_index", None)
                if expansion_handler is not None:
                    expansion_handler(result.current_item)
                    QTimer.singleShot(0, lambda index=result.current_item: expansion_handler(index))
            if getattr(w, "view_mode", mode) != mode:
                w.set_view_mode(mode)
            self.update_ui()
            return True

        if getattr(w, "source_kind", None) == "raw_file":
            target_item, folder_changed = self._raw_boundary_target(step)
            if target_item is None:
                self.update_ui()
                return False
            if folder_changed:
                self.tree_sync.change_series(target_item)
            else:
                self.tree_sync.sync_item(target_item, collapse_previous=False)
            w._open_tree_item(target_item, force=True)
            self.update_ui()
            return True

        provider = self._explorer_provider()
        current = provider.current()
        result = provider.previous() if step < 0 else provider.next()
        if current is None or result is None or result.current_item is current.item:
            self.update_ui()
            return False
        if result.series_changed:
            self.tree_sync.change_series(result.current_item)
        else:
            self.tree_sync.sync_item(result.current_item, collapse_previous=False)
        w._open_tree_item(result.current_item, force=True)
        self.update_ui()
        return True

    def update_ui(self) -> None:
        """Refresh slice text and continuous-navigation button availability."""
        w = self.window
        entries = getattr(w, "dicom_entries", None) or []
        if getattr(w, "source_kind", None) == "dicom" and entries:
            location = self._dicom_provider().current()
            if location is None:
                label, has_previous, has_next = "Slice: -", False, False
            else:
                label = f"Slice: {location.index_in_group + 1}/{max(location.group_size, 1)}"
                has_previous = location.has_previous
                has_next = location.has_next
        elif getattr(w, "source_kind", None) == "raw_file":
            current_item = self._current_explorer_item()
            current_data = current_item.data(0, Qt.UserRole) if current_item is not None else None
            label = (
                f"RAW: {current_item.text(0)}"
                if current_data and current_data[0] == "raw_file"
                else "RAW: -"
            )
            previous_item, _previous_folder_changed = self._raw_boundary_target(-1)
            next_item, _next_folder_changed = self._raw_boundary_target(1)
            has_previous = previous_item is not None
            has_next = next_item is not None
        else:
            location = self._explorer_provider().current()
            label = "Slice: -"
            has_previous = bool(location and location.has_previous)
            has_next = bool(location and location.has_next)

        toolbar = getattr(w, "viewer_toolbar", None)
        if toolbar is not None and hasattr(toolbar, "set_navigation_state"):
            toolbar.set_navigation_state(
                label=label,
                has_previous=has_previous,
                has_next=has_next,
            )
            return
        if hasattr(w, "slice_label"):
            w.slice_label.setText(label)
        if hasattr(w, "prev_btn"):
            w.prev_btn.setEnabled(bool(has_previous))
        if hasattr(w, "next_btn"):
            w.next_btn.setEnabled(bool(has_next))
