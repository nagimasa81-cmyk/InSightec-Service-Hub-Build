from __future__ import annotations

import csv
import html
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QProgressBar, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from src.core.metadata import MetadataManager, StudyMetadata
from src.core.metadata.models import SonicationMetadata, SourceStatus


REQUIRED_FIELDS = {
    "Summary": ("power", "energy", "duration", "frequency", "protocol", "scanplane"),
    "Protocol": ("maxpower", "sonicationduration", "spotsize", "repetitionrate"),
    "MR": ("scan plane", "frequency direction", "coil", "te", "tr", "matrix", "fov", "slice thickness"),
    "Timing": ("mr_scan_start", "mr_scan_end", "sonication_start", "sonication_end"),
    "Skull": ("files", "spot_cues", "element_counts"),
}


def _normalise_key(value: str) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _find_value(mapping: dict[str, Any], requested: str) -> Any:
    wanted = _normalise_key(requested)
    for key, value in mapping.items():
        if _normalise_key(key) == wanted:
            return value
    return None


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


class DiagnosticsTab(QWidget):
    sonicationRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = MetadataManager()
        self.metadata: StudyMetadata | None = None
        self.package = None
        self.load_elapsed_ms = 0.0
        self._rows: list[dict[str, Any]] = []
        self._build_ui()
        self.clear()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Replay Diagnostics")
        title.setStyleSheet("font-size:20px;font-weight:600")
        self.session_label = QLabel("No study loaded")
        self.session_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header.addWidget(title)
        header.addSpacing(14)
        header.addWidget(self.session_label, 1)
        self.refresh_button = QPushButton("Refresh")
        self.export_json_button = QPushButton("Export JSON")
        self.export_csv_button = QPushButton("Export CSV")
        self.export_html_button = QPushButton("Export HTML")
        self.refresh_button.clicked.connect(self.refresh)
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        self.export_csv_button.clicked.connect(lambda: self._export("csv"))
        self.export_html_button.clicked.connect(lambda: self._export("html"))
        for button in (self.refresh_button, self.export_json_button, self.export_csv_button, self.export_html_button):
            header.addWidget(button)
        root.addLayout(header)

        summary = QGridLayout()
        self.health_value = QLabel("--")
        self.health_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.health_value.setMinimumSize(110, 72)
        self.health_value.setStyleSheet("font-size:28px;font-weight:700;border:1px solid #54718a;border-radius:6px")
        summary.addWidget(self._card("Health Score", self.health_value), 0, 0)
        self.coverage_bar = QProgressBar()
        self.coverage_bar.setRange(0, 100)
        self.coverage_bar.setFormat("%p%")
        summary.addWidget(self._card("Metadata Coverage", self.coverage_bar), 0, 1)
        self.resource_summary = QLabel("Loaded 0   Missing 0   Errors 0")
        self.resource_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary.addWidget(self._card("Resources", self.resource_summary), 0, 2)
        self.performance_summary = QLabel("Metadata load: -- ms")
        self.performance_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary.addWidget(self._card("Performance", self.performance_summary), 0, 3)
        root.addLayout(summary)

        self.pages = QTabWidget()
        self.pages.addTab(self._build_metadata_page(), "Metadata")
        self.pages.addTab(self._build_timeline_page(), "Timeline")
        self.pages.addTab(self._build_resources_page(), "Resources")
        self.pages.addTab(self._build_performance_page(), "Performance")
        self.pages.addTab(self._build_report_page(), "Report")
        root.addWidget(self.pages, 1)

    @staticmethod
    def _card(title: str, content: QWidget) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(content)
        return box

    def _build_metadata_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Sonications"))
        self.sonication_list = QListWidget()
        self.sonication_list.currentRowChanged.connect(self._sonication_changed)
        self.sonication_list.itemDoubleClicked.connect(self._jump_to_sonication)
        left_layout.addWidget(self.sonication_list, 1)
        splitter.addWidget(left)

        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        middle_layout.addWidget(QLabel("Metadata Explorer"))
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Item", "Value", "Source / Status"])
        self.metadata_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.metadata_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.metadata_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        middle_layout.addWidget(self.metadata_tree, 1)
        splitter.addWidget(middle)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Warning Center"))
        self.warning_list = QListWidget()
        right_layout.addWidget(self.warning_list, 1)
        right_layout.addWidget(QLabel("Replay Inspector"))
        self.inspector_table = QTableWidget(0, 2)
        self.inspector_table.setHorizontalHeaderLabels(["Item", "Value"])
        self.inspector_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.inspector_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.inspector_table, 2)
        splitter.addWidget(right)

        splitter.setSizes([220, 760, 420])
        layout.addWidget(splitter)
        return page

    def _build_timeline_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.timeline_table = QTableWidget(0, 5)
        self.timeline_table.setHorizontalHeaderLabels(["Sonication", "Source", "Start", "End", "Duration / Status"])
        self.timeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.timeline_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.timeline_table)
        return page

    def _build_resources_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.resource_table = QTableWidget(0, 5)
        self.resource_table.setHorizontalHeaderLabels(["Resource", "State", "Records", "Path", "Error"])
        self.resource_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.resource_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.resource_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.resource_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.resource_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.resource_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.resource_table)
        return page

    def _build_performance_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.performance_table = QTableWidget(0, 2)
        self.performance_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.performance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.performance_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.performance_table)
        return page

    def _build_report_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.report_tree = QTreeWidget()
        self.report_tree.setHeaderLabels(["Category", "Result"])
        self.report_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.report_tree)
        return page

    def clear(self) -> None:
        self.metadata = None
        self.package = None
        self._rows.clear()
        self.session_label.setText("No study loaded")
        self.health_value.setText("--")
        self.coverage_bar.setValue(0)
        self.resource_summary.setText("Loaded 0   Missing 0   Errors 0")
        self.performance_summary.setText("Metadata load: -- ms")
        for widget in (self.sonication_list, self.warning_list):
            widget.clear()
        self.metadata_tree.clear()
        self.report_tree.clear()
        for table in (self.inspector_table, self.timeline_table, self.resource_table, self.performance_table):
            table.setRowCount(0)

    def load_study(self, root: str | Path, package=None) -> None:
        """Load diagnostics from the same workspace used by Replay.

        Metadata XML is preferred, but Replay packages without the XML set must
        still populate Diagnostics instead of leaving the page blank.
        """
        self.package = package
        started = time.perf_counter()
        load_error = ""
        try:
            metadata = self.manager.load(root)
        except Exception as exc:
            load_error = f"Metadata load failed: {type(exc).__name__}: {exc}"
            metadata = StudyMetadata(root=str(Path(root).resolve()))

        self._merge_replay_package(metadata, package)
        if load_error:
            metadata.warnings.insert(0, load_error)

        self.load_elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.metadata = metadata
        self._rebuild()

    def _merge_replay_package(self, metadata: StudyMetadata, package) -> None:
        """Add Replay-discovery results and synthesize sonications when needed."""
        if package is None:
            return

        models = list(getattr(package, "sonications", []) or [])
        replay_records = sum(model.replay_frame_count for model in models)
        temperature_records = sum(len(model.temperature_frames) for model in models)
        spectrum_records = sum(len(model.spectrum_files) for model in models)
        act_records = sum(len(model.act_files) for model in models)
        workspace = str(getattr(package, "workspace", metadata.root))

        metadata.sources["replay"] = SourceStatus(workspace, bool(models), replay_records, None if models else "No replay sonications discovered")
        metadata.sources["temperature"] = SourceStatus(workspace, temperature_records > 0, temperature_records, None if temperature_records else "No temperature RAW frames")
        metadata.sources["spectrum"] = SourceStatus(workspace, spectrum_records > 0, spectrum_records, None if spectrum_records else "No SpectrumMsg files")
        metadata.sources["act"] = SourceStatus(workspace, act_records > 0, act_records, None if act_records else "No ACT files")

        for position, model in enumerate(models, start=1):
            son = metadata.sonications.get(position)
            if son is None:
                son = SonicationMetadata(index=position)
                metadata.sonications[position] = son
            # Preserve parsed workstation values; fill only missing essentials.
            son.summary.setdefault("sonication", position)
            son.summary.setdefault("name", model.name)
            son.summary.setdefault("power", model.planned_power_w)
            son.summary.setdefault("duration", model.actual_duration_s or model.planned_duration_s)
            son.summary.setdefault("frequency", model.main_frequency_hz)
            son.summary.setdefault("replayframes", model.replay_frame_count)
            son.summary.setdefault("temperatureframes", len(model.temperature_frames))
            son.summary.setdefault("spectrumfiles", len(model.spectrum_files))
            son.sources = dict(metadata.sources)

        if models and not metadata.study:
            metadata.study = {
                "source": str(getattr(package, "source", "")),
                "workspace": workspace,
                "sonications": len(models),
            }

    def select_sonication(self, zero_based_index: int) -> None:
        if self.sonication_list.count() <= 0:
            return
        row = max(0, min(int(zero_based_index), self.sonication_list.count() - 1))
        self.sonication_list.setCurrentRow(row)

    def refresh(self) -> None:
        if not self.metadata:
            return
        self.load_study(self.metadata.root, self.package)

    def _rebuild(self) -> None:
        assert self.metadata is not None
        root = Path(self.metadata.root)
        self.session_label.setText(f"{root.name}   |   {len(self.metadata.sonications)} sonication(s)")
        self.sonication_list.clear()
        for index in sorted(self.metadata.sonications):
            son = self.metadata.sonications[index]
            coverage = self._sonication_coverage(son)
            item = QListWidgetItem(f"Sonication {index}    {coverage}%")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.sonication_list.addItem(item)
        self._populate_resources()
        self._populate_warnings()
        self._populate_timeline()
        self._populate_performance()
        coverage = self._overall_coverage()
        health = self._health_score(coverage)
        self.coverage_bar.setValue(coverage)
        self.health_value.setText(f"{health}/100")
        if health >= 95:
            colour = "#2ecc71"
        elif health >= 80:
            colour = "#f1c40f"
        else:
            colour = "#e74c3c"
        self.health_value.setStyleSheet(f"font-size:28px;font-weight:700;color:{colour};border:1px solid #54718a;border-radius:6px")
        self.performance_summary.setText(f"Metadata load: {self.load_elapsed_ms:.1f} ms")
        self._populate_report(coverage, health)
        if self.sonication_list.count():
            self.sonication_list.setCurrentRow(0)

    def _sonication_coverage(self, son) -> int:
        checks: list[bool] = []
        for key in REQUIRED_FIELDS["Summary"]:
            checks.append(_has_value(_find_value(son.summary, key)))
        for key in REQUIRED_FIELDS["Protocol"]:
            checks.append(_has_value(_find_value(son.protocol, key)))
        for key in REQUIRED_FIELDS["MR"]:
            checks.append(_has_value(_find_value(son.mr.fields, key)))
        checks.extend([bool(son.spots), bool(son.skull.files)])
        return int(round(100.0 * sum(checks) / max(1, len(checks))))

    def _overall_coverage(self) -> int:
        if not self.metadata or not self.metadata.sonications:
            return 0
        values = [self._sonication_coverage(son) for son in self.metadata.sonications.values()]
        return int(round(sum(values) / len(values)))

    def _health_score(self, coverage: int) -> int:
        assert self.metadata is not None
        statuses = list(self.metadata.sources.values())
        resource_score = int(round(100 * sum(1 for status in statuses if status.loaded) / max(1, len(statuses))))
        error_penalty = min(25, 5 * sum(1 for status in statuses if status.error))
        warning_penalty = min(20, 2 * len(self.metadata.warnings))
        return max(0, min(100, int(round(coverage * 0.65 + resource_score * 0.35 - error_penalty - warning_penalty))))

    def _populate_resources(self) -> None:
        assert self.metadata is not None
        self.resource_table.setRowCount(0)
        loaded = missing = errors = 0
        for key, status in sorted(self.metadata.sources.items()):
            state = "Loaded" if status.loaded else ("Parse Error" if status.error else "Missing")
            loaded += int(status.loaded)
            errors += int(bool(status.error))
            missing += int(not status.loaded and not status.error)
            row = self.resource_table.rowCount()
            self.resource_table.insertRow(row)
            values = [key, state, str(status.records), status.path or "", status.error or ""]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setForeground(QColor("#2ecc71" if state == "Loaded" else "#e74c3c" if state == "Parse Error" else "#f1c40f"))
                self.resource_table.setItem(row, col, item)
        self.resource_summary.setText(f"Loaded {loaded}   Missing {missing}   Errors {errors}")

    def _populate_warnings(self) -> None:
        assert self.metadata is not None
        self.warning_list.clear()
        for warning in self.metadata.warnings:
            self.warning_list.addItem(warning)
        for index, son in sorted(self.metadata.sonications.items()):
            for category, required in (("Summary", REQUIRED_FIELDS["Summary"]), ("Protocol", REQUIRED_FIELDS["Protocol"]), ("MR", REQUIRED_FIELDS["MR"])):
                mapping = son.summary if category == "Summary" else son.protocol if category == "Protocol" else son.mr.fields
                for key in required:
                    if not _has_value(_find_value(mapping, key)):
                        self.warning_list.addItem(f"Sonication {index}: {category} field missing - {key}")
            if not son.skull.files:
                self.warning_list.addItem(f"Sonication {index}: SkullMeasures missing")
        if not self.warning_list.count():
            self.warning_list.addItem("No validation warnings")

    def _populate_timeline(self) -> None:
        assert self.metadata is not None
        self.timeline_table.setRowCount(0)
        for index, son in sorted(self.metadata.sonications.items()):
            timing = son.timing
            sources = [
                ("MR", timing.mr_scan_start, timing.mr_scan_end),
                ("Sonication", timing.sonication_start, timing.sonication_end),
            ]
            if self.package and 0 < index <= len(self.package.sonications):
                model = self.package.sonications[index - 1]
                sources.extend([
                    ("Replay", "0.000 s", None, f"{model.replay_frame_count} frames"),
                    ("Temperature", "0.000 s", None, f"{len(model.temperature_frames)} frames"),
                    ("Spectrum", "0.000 s", None, f"{len(model.spectrum_files)} files"),
                ])
            for entry in sources:
                name, start, end = entry[:3]
                status = entry[3] if len(entry) > 3 else ("Available" if start or end else "Unavailable")
                row = self.timeline_table.rowCount()
                self.timeline_table.insertRow(row)
                for col, value in enumerate((str(index), name, start or "", end or "", status)):
                    self.timeline_table.setItem(row, col, QTableWidgetItem(str(value)))

    def _populate_performance(self) -> None:
        assert self.metadata is not None
        metrics = [
            ("Metadata load time", f"{self.load_elapsed_ms:.2f} ms"),
            ("Sonications", len(self.metadata.sonications)),
            ("Metadata source count", len(self.metadata.sources)),
            ("Warnings", len(self.metadata.warnings)),
        ]
        if self.package:
            metrics.extend([
                ("Replay frames", sum(s.replay_frame_count for s in self.package.sonications)),
                ("Temperature frames", sum(len(s.temperature_frames) for s in self.package.sonications)),
                ("Magnitude frames", sum(len(s.magnitude_frames) for s in self.package.sonications)),
                ("Spectrum files", sum(len(s.spectrum_files) for s in self.package.sonications)),
                ("ACT files", sum(len(s.act_files) for s in self.package.sonications)),
                ("Workspace", str(self.package.workspace)),
            ])
        self.performance_table.setRowCount(len(metrics))
        for row, (key, value) in enumerate(metrics):
            self.performance_table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.performance_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _populate_report(self, coverage: int, health: int) -> None:
        assert self.metadata is not None
        self.report_tree.clear()
        overview = QTreeWidgetItem(["Overview", f"Health {health}/100, Coverage {coverage}%"])
        overview.addChild(QTreeWidgetItem(["Root", self.metadata.root]))
        overview.addChild(QTreeWidgetItem(["Sonications", str(len(self.metadata.sonications))]))
        overview.addChild(QTreeWidgetItem(["Warnings", str(self.warning_list.count())]))
        self.report_tree.addTopLevelItem(overview)
        resources = QTreeWidgetItem(["Resources", ""])
        for key, status in sorted(self.metadata.sources.items()):
            state = "Loaded" if status.loaded else "Error" if status.error else "Missing"
            resources.addChild(QTreeWidgetItem([key, f"{state}; records={status.records}; {status.error or status.path or ''}"]))
        self.report_tree.addTopLevelItem(resources)
        self.report_tree.expandAll()

    def _sonication_changed(self, row: int) -> None:
        if row < 0 or not self.metadata:
            return
        item = self.sonication_list.item(row)
        index = int(item.data(Qt.ItemDataRole.UserRole))
        son = self.metadata.sonications[index]
        self._populate_metadata_tree(son)
        self._populate_inspector(index, son)

    def _jump_to_sonication(self, item: QListWidgetItem) -> None:
        index = int(item.data(Qt.ItemDataRole.UserRole))
        self.sonicationRequested.emit(index - 1)

    def _populate_metadata_tree(self, son) -> None:
        self.metadata_tree.clear()
        sections = [
            ("Summary", son.summary, son.sources.get("summary")),
            ("Protocol", son.protocol, son.sources.get("protocol")),
            ("Spot", {f"Spot {i+1}": spot for i, spot in enumerate(son.spots)}, son.sources.get("spot")),
            ("Treatment", son.treatment, son.sources.get("treatment")),
            ("Layer", son.layer, son.sources.get("layer")),
            ("MR", son.mr.fields, son.mr.source),
            ("Timing", asdict(son.timing), None),
            ("Skull", asdict(son.skull), None),
        ]
        for title, values, status in sections:
            source_text = ""
            if status:
                source_text = "Loaded" if status.loaded else status.error or "Missing"
            top = QTreeWidgetItem([title, "", source_text])
            self.metadata_tree.addTopLevelItem(top)
            self._append_mapping(top, values)
        self.metadata_tree.expandToDepth(1)

    def _append_mapping(self, parent: QTreeWidgetItem, mapping: Any) -> None:
        if isinstance(mapping, dict):
            for key, value in sorted(mapping.items(), key=lambda pair: str(pair[0])):
                if isinstance(value, (dict, list, tuple)):
                    child = QTreeWidgetItem([str(key), "", ""])
                    parent.addChild(child)
                    self._append_mapping(child, value)
                else:
                    parent.addChild(QTreeWidgetItem([str(key), str(value), ""]))
        elif isinstance(mapping, (list, tuple)):
            for index, value in enumerate(mapping):
                child = QTreeWidgetItem([str(index), "" if isinstance(value, (dict, list, tuple)) else str(value), ""])
                parent.addChild(child)
                if isinstance(value, (dict, list, tuple)):
                    self._append_mapping(child, value)
        else:
            parent.addChild(QTreeWidgetItem(["Value", str(mapping), ""]))

    def _populate_inspector(self, index: int, son) -> None:
        rows = [
            ("Sonication", index),
            ("Coverage", f"{self._sonication_coverage(son)}%"),
            ("Power", _find_value(son.summary, "power") or "Unavailable"),
            ("Measured Power", _find_value(son.summary, "measuredpower") or "Unavailable"),
            ("Energy", _find_value(son.summary, "energy") or "Unavailable"),
            ("Measured Energy", _find_value(son.summary, "measuredenergy") or "Unavailable"),
            ("Duration", _find_value(son.summary, "duration") or "Unavailable"),
            ("Actual Duration", _find_value(son.summary, "actualduration") or "Unavailable"),
            ("Frequency", _find_value(son.summary, "frequency") or "Unavailable"),
            ("Protocol", _find_value(son.summary, "protocol") or _find_value(son.summary, "treatprotocol") or "Unavailable"),
            ("Scan Plane", _find_value(son.summary, "scanplane") or _find_value(son.mr.fields, "scan plane") or "Unavailable"),
            ("Frequency Direction", _find_value(son.mr.fields, "frequency direction") or "Unavailable"),
            ("Spots", len(son.spots)),
            ("Skull files", len(son.skull.files)),
            ("Skull elements", sum(son.skull.element_counts.values())),
        ]
        if self.package and 0 < index <= len(self.package.sonications):
            model = self.package.sonications[index - 1]
            rows.extend([
                ("Replay frames", model.replay_frame_count),
                ("Temperature frames", len(model.temperature_frames)),
                ("Spectrum files", len(model.spectrum_files)),
            ])
        self.inspector_table.setRowCount(len(rows))
        for row, (key, value) in enumerate(rows):
            self.inspector_table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.inspector_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def report_payload(self) -> dict[str, Any]:
        if not self.metadata:
            return {}
        return {
            "commit": "C0045",
            "health_score": self._health_score(self._overall_coverage()),
            "coverage": self._overall_coverage(),
            "metadata_load_ms": round(self.load_elapsed_ms, 3),
            "metadata": self.metadata.to_dict(),
        }

    def _export(self, kind: str) -> None:
        if not self.metadata:
            QMessageBox.information(self, "Replay Diagnostics", "Load a study first.")
            return
        filters = {
            "json": ("JSON report", "JSON (*.json)"),
            "csv": ("CSV report", "CSV (*.csv)"),
            "html": ("HTML report", "HTML (*.html)"),
        }
        title, file_filter = filters[kind]
        default = Path(self.metadata.root).name + f"_diagnostics.{kind}"
        path, _ = QFileDialog.getSaveFileName(self, title, default, file_filter)
        if not path:
            return
        target = Path(path)
        try:
            if kind == "json":
                target.write_text(json.dumps(self.report_payload(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            elif kind == "csv":
                self._export_csv(target)
            else:
                self._export_html(target)
        except Exception as exc:
            QMessageBox.critical(self, "Replay Diagnostics", f"Export failed:\n{exc}")
            return
        QMessageBox.information(self, "Replay Diagnostics", f"Saved:\n{target}")

    def _export_csv(self, path: Path) -> None:
        assert self.metadata is not None
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Sonication", "Category", "Field", "Value", "Available"])
            for index, son in sorted(self.metadata.sonications.items()):
                for category, mapping in (("Summary", son.summary), ("Protocol", son.protocol), ("MR", son.mr.fields)):
                    for key, value in sorted(mapping.items(), key=lambda pair: str(pair[0])):
                        writer.writerow([index, category, key, value, _has_value(value)])
                writer.writerow([index, "Skull", "files", len(son.skull.files), bool(son.skull.files)])
                writer.writerow([index, "Spot", "records", len(son.spots), bool(son.spots)])

    def _export_html(self, path: Path) -> None:
        payload = self.report_payload()
        metadata = payload.get("metadata", {})
        warnings = metadata.get("warnings", [])
        rows = []
        for key, status in metadata.get("sources", {}).items():
            state = "Loaded" if status.get("loaded") else "Error" if status.get("error") else "Missing"
            rows.append(f"<tr><td>{html.escape(str(key))}</td><td>{state}</td><td>{status.get('records', 0)}</td><td>{html.escape(str(status.get('path') or ''))}</td><td>{html.escape(str(status.get('error') or ''))}</td></tr>")
        document = f"""<!doctype html><html><head><meta charset='utf-8'><title>Replay Diagnostics</title>
<style>body{{font-family:Segoe UI,Arial;background:#101820;color:#e8eef3;margin:24px}}.card{{background:#182733;border:1px solid #385367;border-radius:7px;padding:16px;margin-bottom:14px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #385367;padding:7px;text-align:left}}th{{background:#243b4b}}.ok{{color:#2ecc71}}.warn{{color:#f1c40f}}</style></head><body>
<h1>Replay Diagnostics — C0045</h1><div class='card'><h2>Overview</h2><p>Health Score: <b>{payload.get('health_score', 0)}/100</b></p><p>Coverage: <b>{payload.get('coverage', 0)}%</b></p><p>Metadata load: {payload.get('metadata_load_ms', 0)} ms</p><p>Root: {html.escape(str(metadata.get('root', '')))}</p></div>
<div class='card'><h2>Warnings</h2><ul>{''.join(f'<li>{html.escape(str(w))}</li>' for w in warnings) or '<li>None</li>'}</ul></div>
<div class='card'><h2>Resources</h2><table><tr><th>Resource</th><th>State</th><th>Records</th><th>Path</th><th>Error</th></tr>{''.join(rows)}</table></div>
</body></html>"""
        path.write_text(document, encoding="utf-8")
