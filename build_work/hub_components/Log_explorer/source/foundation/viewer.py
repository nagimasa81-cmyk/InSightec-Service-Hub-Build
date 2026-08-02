"""Viewer Foundation fixes for RC1.

Provides a single deterministic viewer initialization path and keeps layout
recovery controls in one place.  No application-specific parser logic lives
here.
"""
from __future__ import annotations

import re

from types import MethodType
from typing import Any, Callable
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QHBoxLayout,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


def _hide_legacy_view_mode(viewer: Any) -> None:
    combo = getattr(viewer, "mode_combo", None)
    if combo is not None:
        combo.hide()
    for label in viewer.findChildren(QLabel):
        if label.text().strip().lower().startswith("view mode"):
            label.hide()


def _active_screen(viewer: Any):
    """Return the screen that contains the parent/viewer, then cursor screen."""
    candidates = [
        getattr(viewer, "parent_window", None),
        viewer.parentWidget() if hasattr(viewer, "parentWidget") else None,
        viewer,
    ]
    for widget in candidates:
        if widget is None:
            continue
        try:
            handle = widget.windowHandle()
            if handle is not None and handle.screen() is not None:
                return handle.screen()
        except Exception:
            pass
        try:
            center = widget.frameGeometry().center()
            screen = QApplication.screenAt(center)
            if screen is not None:
                return screen
        except Exception:
            pass
    try:
        from PySide6.QtGui import QCursor
        screen = QApplication.screenAt(QCursor.pos())
        if screen is not None:
            return screen
    except Exception:
        pass
    return QApplication.primaryScreen()


def _available_geometry(viewer: Any):
    screen = _active_screen(viewer)
    return screen.availableGeometry() if screen is not None else None


def _configure_window(viewer: Any) -> None:
    """Use nearly all vertical work area on the same monitor as the parent."""
    geo = _available_geometry(viewer)
    if geo is None:
        viewer.resize(1100, 700)
        return
    margin = 8
    width = max(760, geo.width() - margin * 2)
    height = max(520, geo.height() - margin * 2)
    viewer.resize(width, height)
    viewer.move(geo.x() + margin, geo.y() + margin)

def _interactive_widths(viewer: Any, pane_index: int) -> None:
    tables = getattr(viewer, "tables", [])
    models = getattr(viewer, "models", [])
    if not (0 <= pane_index < len(tables)):
        return
    table = tables[pane_index]
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionsMovable(False)
    header.setSectionResizeMode(QHeaderView.Interactive)
    model = models[pane_index] if pane_index < len(models) else table.model()
    columns = list(getattr(model, "columns", []) or [])
    default_by_name = {
        "Timestamp": 165,
        "Entry": 60,
        "Level": 65,
        "Code": 75,
        "Category": 105,
        "Message": 520,
        "SourceType": 105,
        "File": 180,
        "Line": 65,
        "Parameter": 180,
        "Value": 180,
        "MainState": 155,
        "Error": 82,
        "ChillerTemp": 105,
        "PrimaryFlowMeter": 105,
        "AbsolutePressure": 105,
        "DynamicPressure": 105,
        "XdTemperature": 105,
        "VacuumLevel": 105,
        "DOLevel": 105,
        "WaterVolume": 105,
        "SecondaryFlowMeter": 105,
    }
    count = model.columnCount() if model is not None else 0
    for col in range(count):
        name = columns[col] if col < len(columns) else ""
        width = default_by_name.get(name, 135)
        # Do not overwrite a width the operator already adjusted.
        if table.columnWidth(col) <= 0 or table.columnWidth(col) > 1400:
            table.setColumnWidth(col, width)
        elif name in default_by_name and not table.property("foundation_widths_initialized"):
            table.setColumnWidth(col, width)
        header.setSectionResizeMode(col, QHeaderView.Interactive)
    table.setProperty("foundation_widths_initialized", True)


def _configure_tables(viewer: Any) -> None:
    for idx, table in enumerate(getattr(viewer, "tables", [])):
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setTextElideMode(Qt.ElideRight)
        _interactive_widths(viewer, idx)


def _install_interactive_width_override(viewer: Any) -> None:
    """Prevent legacy code from restoring Fixed/Stretch modes after a load."""
    def apply_table_column_widths(self: Any, idx: int) -> None:
        _interactive_widths(self, idx)

    viewer.apply_table_column_widths = MethodType(apply_table_column_widths, viewer)


def _connect_time_double_click_once(viewer: Any) -> None:
    for pane, table in enumerate(getattr(viewer, "tables", [])):
        if table.property("foundation_time_connected"):
            continue
        table.doubleClicked.connect(
            lambda _index, idx=pane: viewer.set_time_from_clicked_row(idx)
        )
        table.setProperty("foundation_time_connected", True)


def _polish_buttons(viewer: Any) -> None:
    for button in viewer.findChildren(QPushButton):
        label = button.text().strip().lower()
        if label in {"load visible logs", "load all visible", "load logs"} or "load visible" in label:
            button.setText("LOAD LOGS")
            button.setMinimumHeight(34)
            button.setMinimumWidth(110)


def _reset_layout(viewer: Any) -> None:
    _configure_window(viewer)
    checks = getattr(viewer, "pane_visible_checks", [])
    # Preserve the current 1/2/3/4 pane selection. Reset only geometry/widths.
    current_checked = [bool(cb.isChecked()) for cb in checks]
    if not any(current_checked) and checks:
        current_checked[0] = True
    for index, checkbox in enumerate(checks):
        checkbox.blockSignals(True)
        checkbox.setChecked(current_checked[index])
        checkbox.blockSignals(False)
    update = getattr(viewer, "update_view_mode", None)
    if callable(update):
        update()
    splitter = getattr(viewer, "main_splitter", None)
    if splitter is not None:
        visible = getattr(viewer, "visible_indices", lambda: [0, 1])()
        each = 1000 // max(1, len(visible))
        splitter.setSizes([each if i in visible else 0 for i in range(len(getattr(viewer, "panes", [])))])
    for idx, table in enumerate(getattr(viewer, "tables", [])):
        table.setProperty("foundation_widths_initialized", False)
        _interactive_widths(viewer, idx)
    status = getattr(viewer, "status", None)
    if status is not None:
        status.setText("Viewer layout reset.")


def _fit_columns(viewer: Any, pane_indices=None) -> None:
    indices = list(pane_indices) if pane_indices is not None else list(range(len(getattr(viewer, "tables", []))))
    for idx in indices:
        if idx >= len(getattr(viewer, "tables", [])):
            continue
        table = viewer.tables[idx]
        table.resizeColumnsToContents()
        model = viewer.models[idx]
        for col, name in enumerate(getattr(model, "columns", []) or []):
            current = table.columnWidth(col)
            if name == "Timestamp":
                width = min(190, max(145, current))
            elif name in {"Level", "Error"}:
                width = min(105, max(62, current))
            elif name in {"Message", "Raw"}:
                width = min(620, max(260, current))
            elif name == "MainState":
                width = min(210, max(130, current))
            else:
                width = min(240, max(70, current))
            table.setColumnWidth(col, width)
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
        table.setProperty("foundation_widths_initialized", True)
    status = getattr(viewer, "status", None)
    if status is not None:
        status.setText("Columns fitted automatically after load.")


def _install_layout_buttons(viewer: Any) -> None:
    if getattr(viewer, "foundation_reset_layout_btn", None) is not None:
        return
    root = viewer.layout()
    if root is None:
        return
    bar = QHBoxLayout()
    bar.addStretch(1)
    reset_btn = QPushButton("Reset Layout")
    reset_btn.setToolTip("Reset sizes and default widths without changing the current pane count.")
    reset_btn.clicked.connect(lambda: _reset_layout(viewer))
    bar.addWidget(reset_btn)
    insert_at = max(0, root.count() - 1)
    root.insertLayout(insert_at, bar)
    viewer.foundation_reset_layout_btn = reset_btn
    viewer.foundation_fit_columns_btn = None


def _install_copy_rule_editor(viewer: Any) -> None:
    """Restore editable popup before copying rule text."""
    def copy_rule_text(self: Any, side: Any) -> None:
        idx = self.side_index(side)
        rec = self.selected_record_from_pane(idx)
        if rec is None:
            QMessageBox.information(self, "Copy Rule Text", "Select a row first.")
            return
        # _compact_pattern is resolved from the original method's module globals.
        original = getattr(self, "_foundation_original_copy_rule", None)
        compact = None
        if original is not None:
            func = getattr(original, "__func__", original)
            compact_fn = getattr(func, "__globals__", {}).get("_compact_pattern")
            if callable(compact_fn):
                compact = compact_fn(rec.message or rec.raw)
        suggested = compact if compact is not None else str(rec.message or rec.raw).strip()
        edited, ok = QInputDialog.getMultiLineText(
            self,
            "Copy Rule Text",
            "Edit the rule text, then select OK to copy it:",
            suggested,
        )
        if not ok:
            return
        text = edited.strip()
        if not text:
            QMessageBox.information(self, "Copy Rule Text", "Nothing was copied because the text is empty.")
            return
        QApplication.clipboard().setText(text)
        self.log(f"Copied edited {self.pane_name(idx)} rule text to clipboard: {text}")

    viewer._foundation_original_copy_rule = getattr(viewer, "copy_rule_text", None)
    viewer.copy_rule_text = MethodType(copy_rule_text, viewer)





def _install_pane_filters(viewer: Any) -> None:
    """Add a simple per-pane structured/text filter without changing source rows."""
    if getattr(viewer, "foundation_filter_edits", None) is not None:
        return
    viewer.foundation_filter_edits = []
    viewer.foundation_filter_clear_buttons = []
    original_apply = getattr(viewer, "apply_view_filters")

    def filtered_apply(self: Any, side: Any):
        idx = self.side_index(side)
        # Reproduce the original time-range filter, then apply pane text filter.
        try:
            start, end = self.current_viewer_time_range()
        except Exception as exc:
            QMessageBox.warning(self, "Viewer Time Range", str(exc))
            return
        rows = list(self.all_rows[idx])
        if start or end:
            rows = [r for r in rows if isinstance(r.get("_ts"), object) and (not start or (r.get("_ts") and r.get("_ts") >= start)) and (not end or (r.get("_ts") and r.get("_ts") <= end))]
        raw_term = self.foundation_filter_edits[idx].text().strip() if idx < len(self.foundation_filter_edits) else ""
        term = raw_term.lower()
        if term:
            # Minimal field filter syntax used by CSA/CGA default view, while
            # preserving the existing all-field text filter behavior.
            field_match = re.fullmatch(r"([A-Za-z][A-Za-z _-]*)\s*=\s*(.+)", raw_term)
            if field_match:
                field = field_match.group(1).strip().lower()
                expected = field_match.group(2).strip().lower()
                rows = [r for r in rows if str(next((v for k, v in r.items() if str(k).lower() == field), "")).strip().lower() == expected]
            else:
                rows = [r for r in rows if term in " ".join(str(v) for k, v in r.items() if k != "_ts").lower()]
        cols = self.pane_columns_for_rows(idx, rows)
        self.models[idx].set_rows(rows, cols)
        self.ts_indexes[idx] = sorted([(r["_ts"], i) for i, r in enumerate(rows) if r.get("_ts") is not None], key=lambda x: x[0])
        self._sync_aliases()
        _fit_columns(self, [idx])
        self.log(f"Filter {self.pane_name(idx)}: {len(rows)}/{len(self.all_rows[idx])} rows" + (f" | {term}" if term else ""))

    viewer.apply_view_filters = MethodType(filtered_apply, viewer)

    # Insert one filter row into each pane layout, immediately above its table.
    for idx, pane in enumerate(getattr(viewer, "panes", [])):
        layout = pane.layout()
        if layout is None:
            continue
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setPlaceholderText("Filter this pane (all visible/structured fields)...")
        apply_btn = QPushButton("Filter")
        clear_btn = QPushButton("Clear")
        apply_btn.clicked.connect(lambda _=False, i=idx: viewer.apply_view_filters(i))
        edit.returnPressed.connect(lambda i=idx: viewer.apply_view_filters(i))
        clear_btn.clicked.connect(lambda _=False, i=idx, e=edit: (e.clear(), viewer.apply_view_filters(i)))
        row.addWidget(edit, 1); row.addWidget(apply_btn); row.addWidget(clear_btn)
        # Table is normally the last item in each pane layout.
        layout.insertLayout(max(0, layout.count()-1), row)
        viewer.foundation_filter_edits.append(edit)
        viewer.foundation_filter_clear_buttons.append(clear_btn)

def _install_investigation_button(viewer: Any) -> None:
    if getattr(viewer, "foundation_investigation_btn", None) is not None:
        return
    root = viewer.layout()
    if root is None:
        return

    # Move the existing Log Viewer UI into page 0, then add Investigation Mode
    # as page 1. This preserves the existing viewer instead of opening a new window.
    normal_page = QWidget(viewer)
    normal_layout = QVBoxLayout(normal_page)
    normal_layout.setContentsMargins(0, 0, 0, 0)
    existing_items = []
    while root.count():
        existing_items.append(root.takeAt(0))
    for item in existing_items:
        if item.widget() is not None:
            normal_layout.addWidget(item.widget())
        elif item.layout() is not None:
            normal_layout.addLayout(item.layout())
        elif item.spacerItem() is not None:
            normal_layout.addItem(item.spacerItem())

    stack = QStackedWidget(viewer)
    stack.addWidget(normal_page)

    from foundation.investigation import InvestigationWorkspace
    investigation = InvestigationWorkspace(viewer)
    stack.addWidget(investigation)

    mode_bar = QHBoxLayout()
    button = QPushButton("Investigation Mode")
    button.setCheckable(True)
    button.setToolTip("Switch this Log Viewer between normal viewing and Investigation Mode.")
    mode_label = QLabel("Normal Log Viewer")
    mode_label.setStyleSheet("font-weight:600;color:#334155;")
    mode_bar.addWidget(button)
    mode_bar.addWidget(mode_label)
    mode_bar.addStretch(1)
    root.addLayout(mode_bar)
    root.addWidget(stack, 1)

    def set_mode(enabled: bool) -> None:
        stack.setCurrentIndex(1 if enabled else 0)
        mode_label.setText("Investigation Mode" if enabled else "Normal Log Viewer")
        button.setText("Return to Log Viewer" if enabled else "Investigation Mode")
        if enabled:
            investigation._show_ready_state()

    button.toggled.connect(set_mode)
    investigation.returnRequested.connect(lambda: button.setChecked(False))
    viewer.foundation_investigation_btn = button
    viewer.foundation_investigation_stack = stack
    viewer.foundation_investigation_workspace = investigation

def _install_watersystem_analyzer_button(viewer: Any) -> None:
    if getattr(viewer, "foundation_watersystem_analyzer_btn", None) is not None:
        return
    root = viewer.layout()
    if root is None:
        return

    button = QPushButton("Open WaterSystem Analyzer")
    button.setToolTip("Open the currently loaded WaterSystem source in WaterSystem Analyzer.")

    def selected_watersystem_path() -> Path | None:
        source_folder = Path(getattr(getattr(viewer, "parent_window", None), "source_edit", None).text().strip() or ".") if getattr(getattr(viewer, "parent_window", None), "source_edit", None) is not None else Path(".")
        for pane_index, combo in enumerate(getattr(viewer, "sources", [])):
            if str(combo.currentText()).strip().lower() != "watersystem":
                continue
            rows = getattr(viewer, "all_rows", [[]])[pane_index] if pane_index < len(getattr(viewer, "all_rows", [])) else []
            for row in rows:
                filename = str(row.get("File", "")).strip()
                if not filename:
                    continue
                direct = source_folder / filename
                if direct.exists():
                    return direct
                try:
                    matches = list(source_folder.rglob(filename))
                    if matches:
                        return matches[0]
                except Exception:
                    pass
        return None

    def open_analyzer() -> None:
        source_path = selected_watersystem_path()
        if source_path is None:
            QMessageBox.information(viewer, "WaterSystem Analyzer", "Load WaterSystem in one Viewer pane first.")
            return

        base_candidates = []
        if getattr(sys, "frozen", False):
            base_candidates.append(Path(sys.executable).resolve().parent)
        base_candidates.extend([Path.cwd(), Path(__file__).resolve().parents[1]])
        exe_names = [
            "WaterSystem_Analyzer.exe",
            "Water_system_analyzer.exe",
            "WaterSystemAnalyzer.exe",
        ]
        analyzer = None
        for base in base_candidates:
            for name in exe_names:
                candidate = base / name
                if candidate.exists():
                    analyzer = candidate
                    break
            if analyzer:
                break
        if analyzer is None:
            QMessageBox.information(
                viewer,
                "WaterSystem Analyzer",
                "WaterSystem Analyzer EXE was not found next to this application.\n\n"
                f"Selected file:\n{source_path}",
            )
            return
        try:
            subprocess.Popen([str(analyzer), str(source_path)])
        except Exception as exc:
            QMessageBox.critical(viewer, "WaterSystem Analyzer", f"Failed to open Analyzer.\n\n{exc}")

    button.clicked.connect(open_analyzer)
    bar = QHBoxLayout()
    bar.addWidget(button)
    bar.addStretch(1)
    root.insertLayout(2, bar)
    viewer.foundation_watersystem_analyzer_btn = button

def _post_initialize(viewer: Any) -> None:
    _hide_legacy_view_mode(viewer)
    detail = getattr(viewer, "detail", None)
    if detail is not None:
        detail.hide()
        detail.setMaximumHeight(0)

    checks = getattr(viewer, "pane_visible_checks", [])
    for index, checkbox in enumerate(checks):
        checkbox.setChecked(index < 2)

    refresh = getattr(viewer, "refresh_available_sources", None)
    if callable(refresh):
        refresh()

    _install_interactive_width_override(viewer)
    _install_copy_rule_editor(viewer)
    _configure_tables(viewer)
    _connect_time_double_click_once(viewer)
    _polish_buttons(viewer)
    _install_layout_buttons(viewer)
    _install_pane_filters(viewer)
    _install_investigation_button(viewer)
    _configure_window(viewer)

    original_load_pane = getattr(viewer, "load_pane", None)
    if callable(original_load_pane) and not getattr(viewer, "foundation_load_wrapped", False):
        def load_and_fit(self: Any, side: Any):
            result = original_load_pane(side)
            try:
                _fit_columns(self, [self.side_index(side)])
            except Exception:
                pass
            return result
        viewer.load_pane = MethodType(load_and_fit, viewer)
        viewer.foundation_load_wrapped = True

    update = getattr(viewer, "update_view_mode", None)
    if callable(update):
        update()


def initialize_viewer_foundation(
    viewer: Any,
    parent_window: Any,
    base_initializer: Callable[[Any, Any], None],
) -> None:
    """Create MultiPaneLogViewer through one deterministic initializer."""
    base_initializer(viewer, parent_window)
    _post_initialize(viewer)
