"""RC1 Investigation Mode embedded in the existing Log Viewer.

The mode reuses the existing viewer parser interface. It provides synchronized
log tables plus a lightweight WaterSystem chart without launching another EXE.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from PySide6.QtCore import QPointF, Qt, Signal, QPointF, QRectF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QHeaderView, QMessageBox,
    QTabWidget, QProgressDialog, QApplication,
)

from foundation.spectrum_analysis import SpectrumAnalysisWidget
from foundation.sonication_console import SonicationReplayConsole

TEMPLATES = {
    "Initial Investigation": ["WS", "CSA", "CGA"],
    "Water Investigation": ["WS", "CSA", "CGA", "WaterSystem"],
    "MR Investigation": ["WS", "MRSERVER", "GESYS"],
    "Sonication Investigation": ["WS", "CSA", "CGA", "MRSERVER", "GESYS", "VIMeasure", "ACQUISITION"],
}

CRITICAL_WORDS = (
    "fatal", "error", "watchdog", "restart", "failed", "failure",
    "alarm", "exception", "critical", "timeout",
)
WARNING_WORDS = ("warning", "warn", "retry", "degraded")


def _record_timestamp(record: Any) -> datetime | None:
    return getattr(record, "timestamp", None) or getattr(record, "ts", None)


def _record_message(record: Any) -> str:
    return str(getattr(record, "message", "") or getattr(record, "raw", ""))


def _record_line(record: Any) -> int:
    try:
        return int(getattr(record, "line_number", 0) or getattr(record, "line_no", 0) or getattr(record, "line", 0))
    except Exception:
        return 0


def _level(message: str, existing: str = "") -> str:
    if existing:
        return existing
    lower = message.lower()
    if any(word in lower for word in CRITICAL_WORDS):
        return "Critical"
    if any(word in lower for word in WARNING_WORDS):
        return "Warning"
    return ""


def _structured_fields(record: Any) -> dict[str, Any]:
    raw = getattr(record, "raw", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class WaterSystemChart(QWidget):
    timeSelected = Signal(datetime)

    SERIES = [
        ("DOLevel", "DO Level"),
        ("VacuumLevel", "Vacuum"),
        ("PrimaryFlowMeter", "Primary Flow"),
        ("SecondaryFlowMeter", "Secondary Flow"),
        ("ChillerTemp", "Chiller Temp"),
        ("XdTemperature", "XD Temp"),
        ("4vI", "4vI"), ("4vV", "4vV"),
        ("-6vI", "-6vI"), ("-6vV", "-6vV"),
        ("6vI", "6vI"), ("6vV", "6vV"),
        ("FE_48vI", "FE 48vI"), ("FE_48vV", "FE 48vV"),
        ("ER_48vI", "ER 48vI"), ("ER_48vV", "ER 48vV"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.records: list[Any] = []
        self.visible_series: set[str] = set()
        self.cursor_time: datetime | None = None
        self.setMinimumHeight(260)
        self.setMouseTracking(True)

    def set_records(self, records: list[Any]) -> None:
        self.records = [r for r in records if _record_timestamp(r) is not None]
        self.update()

    def set_series_visible(self, key: str, visible: bool) -> None:
        if visible:
            self.visible_series.add(key)
        else:
            self.visible_series.discard(key)
        self.update()

    def set_cursor_time(self, timestamp: datetime | None) -> None:
        self.cursor_time = timestamp
        self.update()

    def available_series(self) -> list[tuple[str, str]]:
        return [(key, label) for key, label in self.SERIES if len(self._points(key)) >= 2]

    def _points(self, key: str) -> list[tuple[datetime, float]]:
        result: list[tuple[datetime, float]] = []
        for record in self.records:
            fields = _structured_fields(record)
            value = fields.get(key)
            try:
                result.append((_record_timestamp(record), float(value)))
            except Exception:
                continue
        return result

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        plot = self.rect().adjusted(58, 24, -18, -42)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRect(plot)

        if not self.records:
            painter.setPen(QColor("#64748B"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Load WaterSystem or VIMeasure data to display the chart.")
            return

        timestamps = [_record_timestamp(r) for r in self.records if _record_timestamp(r) is not None]
        if len(timestamps) < 2:
            return
        start, end = min(timestamps), max(timestamps)
        duration = max(0.001, (end - start).total_seconds())

        palette = [QColor("#005DAA"), QColor("#D97706"), QColor("#059669"), QColor("#7C3AED"), QColor("#DC2626"), QColor("#0891B2")]
        legend_x = plot.left()
        for series_index, (key, label) in enumerate(self.SERIES):
            if key not in self.visible_series:
                continue
            points = self._points(key)
            if len(points) < 2:
                continue
            values = [value for _, value in points]
            low, high = min(values), max(values)
            span = max(0.001, high - low)
            color = palette[series_index % len(palette)]
            painter.setPen(QPen(color, 1.6))
            poly: list[QPointF] = []
            for ts, value in points:
                x = plot.left() + ((ts - start).total_seconds() / duration) * plot.width()
                y = plot.bottom() - ((value - low) / span) * plot.height()
                poly.append(QPointF(x, y))
            for i in range(1, len(poly)):
                painter.drawLine(poly[i - 1], poly[i])
            painter.fillRect(QRectF(legend_x, 5, 12, 3), color)
            painter.setPen(QColor("#334155"))
            painter.drawText(int(legend_x + 16), 12, label)
            legend_x += 105

        if self.cursor_time is not None and start <= self.cursor_time <= end:
            x = plot.left() + ((self.cursor_time - start).total_seconds() / duration) * plot.width()
            painter.setPen(QPen(QColor("#EF4444"), 1.5, Qt.DashLine))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

        painter.setPen(QColor("#64748B"))
        painter.drawText(plot.left(), self.height() - 15, start.strftime("%H:%M:%S"))
        end_text = end.strftime("%H:%M:%S")
        painter.drawText(plot.right() - 60, self.height() - 15, end_text)

    def mousePressEvent(self, event) -> None:
        if not self.records:
            return
        plot = self.rect().adjusted(58, 24, -18, -42)
        if not plot.contains(event.position().toPoint()):
            return
        timestamps = [_record_timestamp(r) for r in self.records if _record_timestamp(r) is not None]
        start, end = min(timestamps), max(timestamps)
        ratio = max(0.0, min(1.0, (event.position().x() - plot.left()) / max(1, plot.width())))
        selected = start + (end - start) * ratio
        self.cursor_time = selected
        self.update()
        self.timeSelected.emit(selected)



class AcquisitionChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.series = "Event density"
        self.setMinimumHeight(320)

    def set_rows(self, rows):
        self.rows = list(rows or [])
        self.update()

    def set_series(self, name):
        self.series = str(name)
        self.update()

    def _points(self):
        buckets = {}
        for row in self.rows:
            timestamp = row.get("_ts")
            if timestamp is None:
                continue
            key = timestamp.replace(second=0, microsecond=0)
            message = str(row.get("Message", ""))

            if self.series == "Dangerous channels":
                match = re.search(r"Detected <(\d+)> high reflection channels", message)
                if match:
                    buckets[key] = float(match.group(1))
            elif self.series == "Acoustic power":
                match = re.search(r"(?:m_PowerS|SonicAcousticPower)<([+-]?\d+(?:\.\d+)?)>", message)
                if match:
                    buckets[key] = float(match.group(1))
            elif self.series == "Reflection max":
                match = re.search(r"Max Value=\s*\(([+-]?\d+(?:\.\d+)?)\)", message)
                if match:
                    buckets[key] = float(match.group(1))
            elif self.series == "XD impedance":
                match = re.search(r"Xd Impedance:\s*([+-]?\d+(?:\.\d+)?)", message)
                if match:
                    buckets[key] = float(match.group(1))
            elif self.series == "Spectrum save events":
                if "saving fft data" in message.lower() or "spectrum_" in message.lower():
                    buckets[key] = buckets.get(key, 0.0) + 1.0
            elif self.series == "Sonication state":
                if "sonication" in message.lower():
                    buckets[key] = buckets.get(key, 0.0) + 1.0
            else:
                buckets[key] = buckets.get(key, 0.0) + 1.0

        return sorted(buckets.items())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        plot = self.rect().adjusted(65, 24, -20, -48)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRect(plot)

        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        for tick in range(1, 5):
            y = plot.top() + tick * plot.height() / 5.0
            painter.drawLine(
                QPointF(plot.left(), y),
                QPointF(plot.right(), y),
            )

        points = self._points()
        if len(points) < 1:
            painter.setPen(QColor("#64748B"))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                f"No plottable Acquisition data for: {self.series}",
            )
            return

        values = [value for _, value in points]
        minimum = min(values)
        maximum = max(values)
        if maximum <= minimum:
            maximum = minimum + 1.0

        painter.setPen(QPen(QColor("#005DAA"), 1.6))
        previous = None
        for index, (_, value) in enumerate(points):
            x = plot.left() + index * plot.width() / max(1, len(points) - 1)
            y = plot.bottom() - (value - minimum) / (maximum - minimum) * plot.height()
            point = QPointF(x, y)
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point

        painter.setPen(QColor("#334155"))
        painter.drawText(plot.left(), self.height() - 15, str(points[0][0]))
        painter.drawText(plot.right() - 130, self.height() - 15, str(points[-1][0]))
        painter.drawText(8, plot.top() + 16, self.series)


class AcquisitionDashboard(QWidget):
    def __init__(self, investigation):
        super().__init__(investigation)
        self.investigation = investigation
        self.rows = []

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        title = QLabel("Acquisition Dashboard")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#005DAA;")
        self.series_combo = QComboBox()
        self.series_combo.addItems([
            "Event density",
            "Acoustic power",
            "Reflection max",
            "Dangerous channels",
            "XD impedance",
            "Spectrum save events",
            "Sonication state",
        ])
        self.series_combo.currentTextChanged.connect(self._series_changed)
        refresh = QPushButton("Refresh from Viewer")
        refresh.clicked.connect(self.refresh)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QLabel("Chart:"))
        top.addWidget(self.series_combo)
        top.addWidget(refresh)
        root.addLayout(top)

        self.summary = QLabel("Load ACQUISITION in a Viewer pane, then refresh.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "background:#EAF2F8;border:1px solid #CBD5E1;"
            "border-radius:4px;padding:8px;"
        )
        self.summary.setMaximumHeight(70)
        root.addWidget(self.summary)

        self.cards = QLabel()
        self.cards.setWordWrap(True)
        self.cards.setStyleSheet(
            "background:#F8FAFC;border:1px solid #CBD5E1;"
            "border-radius:4px;padding:8px;font-size:13px;"
        )
        self.cards.setMaximumHeight(95)
        root.addWidget(self.cards)

        self.chart = AcquisitionChart()
        self.chart.setMinimumHeight(360)

        self.sonication_table = QTableWidget(0, 6)
        self.sonication_table.setHorizontalHeaderLabels([
            "Sonication", "Time", "Power", "Reflection", "Danger Ch.", "Spectrum"
        ])
        self.sonication_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.events = QTableWidget(0, 4)
        self.events.setHorizontalHeaderLabels(
            ["Timestamp", "Category", "Value", "Message"]
        )
        self.events.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.detail_tabs = QTabWidget()
        self.detail_tabs.addTab(self.sonication_table, "Sonication Summary")
        self.detail_tabs.addTab(self.events, "Selected Series Events")
        self.detail_tabs.setMinimumHeight(180)

        self.dashboard_splitter = QSplitter(Qt.Vertical)
        self.dashboard_splitter.addWidget(self.chart)
        self.dashboard_splitter.addWidget(self.detail_tabs)
        self.dashboard_splitter.setStretchFactor(0, 3)
        self.dashboard_splitter.setStretchFactor(1, 1)
        self.dashboard_splitter.setSizes([540, 230])
        root.addWidget(self.dashboard_splitter, 1)

    def set_records(self, rows) -> None:
        self.rows = list(rows or [])
        self.chart.set_rows(self.rows)
        self._update_summary()
        self._update_events()

    def refresh(self):
        rows = list(
            self.investigation.source_records.get("ACQUISITION", [])
        )

        if not rows:
            viewer = self.investigation.viewer
            for index, combo in enumerate(viewer.sources):
                if combo.currentText().upper() == "ACQUISITION":
                    rows.extend(viewer.all_rows[index])

        self.set_records(rows)

    def _series_changed(self, name):
        self.chart.set_series(name)
        self._update_events()

    def _update_summary(self):
        messages = [str(row.get("Message", "")) for row in self.rows]
        summary = {
            "rows": len(self.rows),
            "sonication": sum("SONICATION" in msg for msg in messages),
            "reflection": sum("Reflection" in msg for msg in messages),
            "spectrum": sum("Spectrum" in msg for msg in messages),
            "danger": sum("dangerous channel" in msg.lower() for msg in messages),
        }
        self.summary.setText(
            f"Rows: {summary['rows']:,} | "
            f"Sonication events: {summary['sonication']:,} | "
            f"Reflection events: {summary['reflection']:,} | "
            f"Spectrum events: {summary['spectrum']:,} | "
            f"Dangerous-channel events: {summary['danger']:,}"
        )
        self.cards.setText(
            "<b>Sonication Investigation Prototype</b><br>"
            f"Acquisition rows: {summary['rows']:,} &nbsp; "
            f"Sonication markers: {summary['sonication']:,} &nbsp; "
            f"Reflection markers: {summary['reflection']:,} &nbsp; "
            f"Spectrum saves: {summary['spectrum']:,}<br>"
            "Use chart selection to compare power, reflection, dangerous "
            "channels, impedance and spectrum-save timing."
        )
        self._populate_sonication_table()

    def _populate_sonication_table(self):
        rows = []
        current = None
        for row in self.rows:
            message = str(row.get("Message", ""))
            timestamp = str(row.get("Timestamp", "") or row.get("_ts", ""))
            if "SONICATION" in message.upper():
                current = {
                    "id": len(rows) + 1,
                    "time": timestamp,
                    "power": "",
                    "reflection": "",
                    "danger": "",
                    "spectrum": "",
                }
                rows.append(current)
            if current is None:
                continue
            power = re.search(r"(?:m_PowerS|SonicAcousticPower)<([+-]?\d+(?:\.\d+)?)>", message)
            reflection = re.search(r"Max Value=\s*\(([+-]?\d+(?:\.\d+)?)\)", message)
            danger = re.search(r"Detected <(\d+)> high reflection channels", message)
            if power:
                current["power"] = power.group(1)
            if reflection:
                current["reflection"] = reflection.group(1)
            if danger:
                current["danger"] = danger.group(1)
            if "spectrum_" in message.lower() or "saving fft data" in message.lower():
                current["spectrum"] = "Yes"

        self.sonication_table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            values = [
                item["id"], item["time"], item["power"],
                item["reflection"], item["danger"], item["spectrum"],
            ]
            for c, value in enumerate(values):
                self.sonication_table.setItem(r, c, QTableWidgetItem(str(value)))

    def _update_events(self):
        selected = self.series_combo.currentText()
        interesting = []
        patterns = {
            "Acoustic power": re.compile(r"(?:m_PowerS|SonicAcousticPower)<([+-]?\d+(?:\.\d+)?)>"),
            "Reflection max": re.compile(r"Max Value=\s*\(([+-]?\d+(?:\.\d+)?)\)"),
            "Dangerous channels": re.compile(r"Detected <(\d+)> high reflection channels"),
            "XD impedance": re.compile(r"Xd Impedance:\s*([+-]?\d+(?:\.\d+)?)"),
            "Spectrum save events": re.compile(r"(Spectrum_[^\s]+|Saving FFT data[^\r\n]*)", re.I),
            "Sonication state": re.compile(r"(SONICATION[^\r\n]*)", re.I),
        }
        pattern = patterns.get(selected)

        for row in self.rows:
            message = str(row.get("Message", ""))
            value = ""
            if pattern is not None:
                match = pattern.search(message)
                if not match:
                    continue
                value = match.group(1)
            elif not any(
                token in message
                for token in (
                    "SONICATION", "Reflection", "Spectrum",
                    "Halt", "QuickReset", "dangerous channel",
                )
            ):
                continue

            interesting.append((
                str(row.get("Timestamp", "")),
                selected,
                value,
                message,
            ))

        interesting = interesting[-500:]
        self.events.setRowCount(len(interesting))
        for row_index, values in enumerate(interesting):
            for column, value in enumerate(values):
                self.events.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

class InvestigationWorkspace(QWidget):
    returnRequested = Signal()

    def __init__(self, viewer: Any):
        super().__init__(viewer)
        self.viewer = viewer

        # Commit0027: Investigation-owned Viewer controls.
        self.viewer_control_bar = QWidget(self)
        viewer_control_layout = QHBoxLayout(self.viewer_control_bar)
        viewer_control_layout.setContentsMargins(0, 0, 0, 0)
        viewer_control_layout.addWidget(QLabel("Viewers:"))

        self.viewer_count_combo = QComboBox()
        self.viewer_count_combo.addItems(["1", "2", "3", "4"])
        current_count = max(1, len(self.viewer.visible_indices()))
        self.viewer_count_combo.setCurrentText(str(current_count))
        self.viewer_count_combo.currentTextChanged.connect(
            self._change_viewer_count
        )
        viewer_control_layout.addWidget(self.viewer_count_combo)

        self.equal_widths_button = QPushButton("Equal Widths")
        self.equal_widths_button.clicked.connect(
            self._equalize_viewer_widths
        )
        viewer_control_layout.addWidget(self.equal_widths_button)

        viewer_control_layout.addSpacing(12)
        viewer_control_layout.addWidget(QLabel("Rows/source:"))
        self.row_limit_combo = QComboBox()
        self.row_limit_combo.addItem("1,000 (Fastest)", 1000)
        self.row_limit_combo.addItem("5,000 (Recommended)", 5000)
        self.row_limit_combo.addItem("10,000", 10000)
        self.row_limit_combo.addItem("25,000", 25000)
        self.row_limit_combo.addItem("50,000 (Slow)", 50000)
        self.row_limit_combo.setCurrentIndex(1)
        self.row_limit_combo.currentIndexChanged.connect(
            self._row_limit_changed
        )
        viewer_control_layout.addWidget(self.row_limit_combo)
        viewer_control_layout.addStretch(1)
        self.tables: dict[str, QTableWidget] = {}
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self.source_records: dict[str, list[Any]] = {}
        self._syncing = False
        self.max_visible_rows_per_source = 5000
        self.max_timeline_items = 5000
        self._analysis_running = False
        self._analysis_cancelled = False
        self._build_ui()
        self._show_ready_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        self.analysis_tabs = QTabWidget()
        root.addWidget(self.analysis_tabs, 1)

        investigation_page = QWidget()
        investigation_root = QVBoxLayout(investigation_page)
        investigation_root.setContentsMargins(4, 4, 4, 4)
        self.analysis_tabs.addTab(investigation_page, "Investigation")

        top = QHBoxLayout()
        title = QLabel("Investigation Mode")
        title.setStyleSheet("font-size:20px;font-weight:700;color:#005DAA;")
        self.template = QComboBox()
        self.template.addItems(TEMPLATES.keys())
        self.view_mode = QComboBox()
        self.view_mode.addItems(["Logs", "WaterSystem Chart", "Logs + Chart"])
        self.view_mode.setCurrentText("Logs + Chart")
        self.view_mode.currentTextChanged.connect(self.apply_view_mode)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search visible investigation logs...")
        self.search.textChanged.connect(self.apply_search)
        self.tolerance = QComboBox()
        for text, value in [("Exact", 0), ("±1 sec", 1), ("±5 sec", 5), ("±10 sec", 10), ("±30 sec", 30)]:
            self.tolerance.addItem(text, value)
        self.tolerance.setCurrentIndex(2)
        self.start_analysis_btn = QPushButton("Start Analysis")
        self.start_analysis_btn.setToolTip(
            "Start the selected Investigation profile. Opening Investigation "
            "Mode itself does not load or process records."
        )
        self.start_analysis_btn.clicked.connect(self.load_template)

        reload_btn = QPushButton("Reload Analysis")
        reload_btn.clicked.connect(self.load_template)
        close_btn = QPushButton("Return to Log Viewer")
        close_btn.clicked.connect(self.returnRequested.emit)
        top.addWidget(title)
        top.addWidget(QLabel("Profile:"))
        top.addWidget(self.template)
        top.addWidget(QLabel("View:"))
        top.addWidget(self.view_mode)
        top.addWidget(QLabel("Sync:"))
        top.addWidget(self.tolerance)
        top.addWidget(self.search, 1)
        top.addWidget(self.start_analysis_btn)
        top.addWidget(reload_btn)
        top.addWidget(close_btn)
        investigation_root.addLayout(top)
        investigation_root.addWidget(self.viewer_control_bar)
        self.analysis_status = QLabel()
        self.analysis_status.setWordWrap(True)
        self.analysis_status.setStyleSheet(
            "background:#EAF2F8;border:1px solid #CBD5E1;"
            "border-radius:4px;padding:7px;color:#334155;"
        )
        investigation_root.addWidget(self.analysis_status)

        self.main_vertical = QSplitter(Qt.Vertical)
        investigation_root.addWidget(self.main_vertical, 1)

        self.logs_host = QWidget()
        self.logs_layout = QHBoxLayout(self.logs_host)
        self.logs_layout.setContentsMargins(0, 0, 0, 0)
        self.main_vertical.addWidget(self.logs_host)

        chart_host = QWidget()
        chart_layout = QVBoxLayout(chart_host)
        chart_controls = QHBoxLayout()
        chart_controls.addWidget(QLabel("Structured Chart (WaterSystem / VIMeasure):"))
        self.chart_checks: dict[str, QCheckBox] = {}
        for key, label in WaterSystemChart.SERIES:
            check = QCheckBox(label)
            check.setChecked(False)
            check.setVisible(False)
            check.toggled.connect(lambda checked, k=key: self.chart.set_series_visible(k, checked))
            chart_controls.addWidget(check)
            self.chart_checks[key] = check
        chart_controls.addStretch(1)
        chart_layout.addLayout(chart_controls)
        self.chart = WaterSystemChart()
        self.chart.timeSelected.connect(self.sync_all_to_time)
        chart_layout.addWidget(self.chart, 1)
        self.main_vertical.addWidget(chart_host)
        self.chart_host = chart_host

        lower = QSplitter(Qt.Horizontal)
        self.main_vertical.addWidget(lower)
        self.main_vertical.setSizes([430, 300, 180])

        timeline_box = QWidget(); timeline_layout = QVBoxLayout(timeline_box)
        header = QHBoxLayout(); header.addWidget(QLabel("Critical Timeline"))
        self.show_critical = QCheckBox("Critical"); self.show_warning = QCheckBox("Warning")
        self.show_critical.setChecked(True); self.show_warning.setChecked(True)
        self.show_critical.toggled.connect(self.apply_search); self.show_warning.toggled.connect(self.apply_search)
        header.addStretch(); header.addWidget(self.show_critical); header.addWidget(self.show_warning)
        timeline_layout.addLayout(header)
        self.summary = QLabel("Critical: 0   Warning: 0   Restart: 0   Watchdog: 0   Timeout: 0")
        timeline_layout.addWidget(self.summary)
        self.timeline = QListWidget(); self.timeline.itemClicked.connect(self.timeline_jump)
        timeline_layout.addWidget(self.timeline)
        lower.addWidget(timeline_box)

        bookmark_box = QWidget(); bookmark_layout = QVBoxLayout(bookmark_box)
        bookmark_layout.addWidget(QLabel("Bookmarks"))
        buttons = QHBoxLayout(); add_btn = QPushButton("Add Selected"); export_btn = QPushButton("Export CSV")
        add_btn.clicked.connect(self.add_bookmark); export_btn.clicked.connect(self.export_bookmarks)
        buttons.addWidget(add_btn); buttons.addWidget(export_btn)
        bookmark_layout.addLayout(buttons)
        self.bookmarks = QListWidget(); self.bookmarks.itemClicked.connect(self.bookmark_jump)
        bookmark_layout.addWidget(self.bookmarks)
        lower.addWidget(bookmark_box)

        notes_box = QWidget(); notes_layout = QVBoxLayout(notes_box)
        notes_layout.addWidget(QLabel("Investigation Notes"))
        self.notes = QTextEdit(); self.notes.setPlaceholderText("Findings, actions, and next steps...")
        notes_layout.addWidget(self.notes)
        lower.addWidget(notes_box)

        self.acquisition_dashboard = AcquisitionDashboard(self)
        self.analysis_tabs.addTab(
            self.acquisition_dashboard,
            "Acquisition Dashboard",
        )

        self.spectrum_analysis = SpectrumAnalysisWidget(self)
        self.analysis_tabs.addTab(self.spectrum_analysis, "Spectrum Analysis")

        self.sonication_console = SonicationReplayConsole(self)
        self.sonication_console.timeChanged.connect(self.sync_all_to_time)
        self.analysis_tabs.addTab(
            self.sonication_console,
            "Sonication Replay",
        )
        self.analysis_tabs.currentChanged.connect(self._analysis_tab_changed)

        self.setStyleSheet("""
            QWidget { background:#F4F7FB; font-family:Segoe UI; }
            QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox {
                background:white; border:1px solid #CBD5E1; border-radius:4px;
            }
            QPushButton { background:#005DAA; color:white; border:0; border-radius:4px; padding:7px 11px; }
            QPushButton:hover { background:#0079C2; }
            QHeaderView::section { background:#EAF2F8; padding:5px; border:0; font-weight:600; }
        """)

    def _show_ready_state(self) -> None:
        self.analysis_status.setText(
            "Ready. Select an Investigation profile and row limit, then press "
            "Start Analysis. No records are processed when Investigation Mode is opened."
        )
        self.start_analysis_btn.setEnabled(True)

    def _progress_checkpoint(
        self,
        progress,
        value: int,
        label: str,
    ) -> bool:
        progress.setValue(max(progress.minimum(), min(progress.maximum(), value)))
        progress.setLabelText(label)
        QApplication.processEvents()
        if progress.wasCanceled():
            self._analysis_cancelled = True
            self.analysis_status.setText(
                "Analysis cancelled. The previously loaded Investigation view "
                "has been retained where possible."
            )
            return False
        return True

    def _select_visible_records(self, records):
        total = len(records)
        limit = max(1000, int(self.max_visible_rows_per_source))
        if total <= limit:
            return list(records), total, False

        # Keep the beginning and end, plus regularly sampled records.
        head_count = min(5000, limit // 5)
        tail_count = min(5000, limit // 5)
        middle_budget = max(0, limit - head_count - tail_count)
        middle_start = head_count
        middle_end = max(middle_start, total - tail_count)
        middle_length = max(0, middle_end - middle_start)

        selected = list(records[:head_count])
        if middle_budget and middle_length:
            step = max(1.0, middle_length / middle_budget)
            selected.extend(
                records[min(middle_end - 1, middle_start + int(index * step))]
                for index in range(middle_budget)
            )
        selected.extend(records[max(head_count, total - tail_count):])
        return selected[:limit], total, True

    def _analysis_tab_changed(self, index: int) -> None:
        widget = self.analysis_tabs.widget(index)

        if (
            hasattr(self, "acquisition_dashboard")
            and widget is self.acquisition_dashboard
            and not self.acquisition_dashboard.rows
        ):
            self.acquisition_dashboard.refresh()

        if (
            hasattr(self, "spectrum_analysis")
            and widget is self.spectrum_analysis
            and not self.spectrum_analysis.dumps
        ):
            self.spectrum_analysis.use_loaded_sources()

    def _row_limit_changed(self, index: int) -> None:
        value = self.row_limit_combo.itemData(index)
        if isinstance(value, int) and value > 0:
            self.max_visible_rows_per_source = value
            self.analysis_status.setText(
                f"Display limit set to {value:,} representative rows per source. "
                "Press Start Analysis or Reload Analysis to apply."
            )

    def _change_viewer_count(self, value: str) -> None:
        count = max(1, min(4, int(value)))
        viewer = self.viewer

        for index in range(viewer.MAX_PANES):
            checkbox = viewer.show_checks[index]
            checkbox.setChecked(index < count)

        viewer.update_view_mode()
        self._equalize_viewer_widths()

    def _equalize_viewer_widths(self) -> None:
        viewer = self.viewer
        visible = viewer.visible_indices()
        if not visible:
            return

        sizes = [
            1000 if index in visible else 0
            for index in range(viewer.MAX_PANES)
        ]
        viewer.main_splitter.setSizes(sizes)

    def apply_view_mode(self) -> None:
        mode = self.view_mode.currentText()
        has_chart = bool(self.chart.available_series())
        self.logs_host.setVisible(mode in {"Logs", "Logs + Chart"})
        self.chart_host.setVisible(has_chart and mode in {"Logs + Chart", "Chart Only"})

    def _clear_panes(self) -> None:
        while self.logs_layout.count():
            item = self.logs_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.tables.clear(); self.rows.clear(); self.source_records.clear()

    def load_template(self) -> None:
        if self._analysis_running:
            return

        self._analysis_running = True
        self._analysis_cancelled = False
        self.start_analysis_btn.setEnabled(False)

        profile = self.template.currentText()
        sources = TEMPLATES.get(profile, [])
        progress = QProgressDialog(
            f"Preparing {profile}...",
            "Cancel",
            0,
            1000,
            self,
        )
        progress.setWindowTitle("Investigation Mode")
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        loaded_sources = 0
        total_indexed = 0
        total_visible = 0

        try:
            if not self._progress_checkpoint(
                progress,
                10,
                f"Preparing {profile}. No data has been changed yet...",
            ):
                return

            self._clear_panes()
            self.analysis_status.setText(
                f"Running {profile}. Press Cancel to stop after the current batch."
            )

            total_sources = max(1, len(sources))

            for source_index, source in enumerate(sources):
                source_base = 40 + int(source_index * 650 / total_sources)
                next_source_base = 40 + int((source_index + 1) * 650 / total_sources)

                if not self._progress_checkpoint(
                    progress,
                    source_base,
                    f"Reading {source} ({source_index + 1}/{total_sources})...",
                ):
                    return

                try:
                    records_obj = self.viewer.source_to_records(source, progress)
                    records = records_obj if isinstance(records_obj, list) else list(records_obj or [])
                    progress.setRange(0, 1000)
                    progress.setValue(source_base)
                    QApplication.processEvents()
                except Exception as exc:
                    records = []
                    QMessageBox.warning(
                        self,
                        "Investigation Mode",
                        f"{source} could not be loaded.\n\n{exc}",
                    )

                if progress.wasCanceled():
                    self._analysis_cancelled = True
                    return

                if not records:
                    continue

                visible_records, source_total, sampled = self._select_visible_records(records)
                total_indexed += source_total
                total_visible += len(visible_records)
                self.source_records[source] = visible_records

                converted = []
                batch_size = 1000
                record_count = max(1, len(visible_records))

                for record_index, record in enumerate(visible_records):
                    if record_index % batch_size == 0:
                        fraction = record_index / record_count
                        stage_value = source_base + int(
                            (next_source_base - source_base) * fraction
                        )
                        label = (
                            f"Indexing {source}: {record_index:,}/"
                            f"{len(visible_records):,} visible rows"
                        )
                        if sampled:
                            label += f" from {source_total:,} total rows"
                        if not self._progress_checkpoint(
                            progress,
                            stage_value,
                            label,
                        ):
                            return

                    ts = _record_timestamp(record)
                    fields = _structured_fields(record)

                    if fields:
                        message = str(
                            fields.get("MainState")
                            or fields.get("Status")
                            or fields.get("State")
                            or ""
                        )
                        detail = str(
                            fields.get("Error")
                            or fields.get("SubStatus")
                            or _record_message(record)
                            or ""
                        )
                        message = (message + " " + detail).strip()
                    else:
                        message = _record_message(record)

                    converted.append({
                        "timestamp": ts,
                        "time": (
                            ts.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                            if isinstance(ts, datetime)
                            else ""
                        ),
                        "message": message,
                        "level": _level(
                            message,
                            str(getattr(record, "level", "") or ""),
                        ),
                        "line": _record_line(record),
                    })

                self.rows[source] = converted
                self.logs_layout.addWidget(self._make_pane(source), 1)
                loaded_sources += 1

                source_note = (
                    f"{len(converted):,} displayed from {source_total:,}"
                    if sampled
                    else f"{len(converted):,} rows"
                )
                self.analysis_status.setText(
                    f"{source} indexed: {source_note}. "
                    f"Loaded sources: {loaded_sources}."
                )

            progress.setRange(0, 1000)
            if not self._progress_checkpoint(
                progress,
                720,
                "Detecting chart series...",
            ):
                return

            chart_records = (
                self.source_records.get("WaterSystem", [])
                + self.source_records.get("VIMeasure", [])
            )
            self.chart.set_records(chart_records)
            available = dict(self.chart.available_series())
            default_keys = [
                key
                for key in (
                    "DOLevel",
                    "VacuumLevel",
                    "PrimaryFlowMeter",
                    "SecondaryFlowMeter",
                    "4vI",
                    "4vV",
                )
                if key in available
            ]
            self.chart.visible_series = set(default_keys[:4])

            for key, check in self.chart_checks.items():
                check.blockSignals(True)
                check.setVisible(key in available)
                check.setChecked(key in self.chart.visible_series)
                check.blockSignals(False)

            has_chart = bool(available)
            self.chart_host.setVisible(has_chart)
            self.view_mode.blockSignals(True)
            self.view_mode.clear()
            self.view_mode.addItem("Logs")
            if has_chart:
                self.view_mode.addItems(["Logs + Chart", "Chart Only"])
                self.view_mode.setCurrentText(
                    "Logs + Chart"
                    if profile in {
                        "Water Investigation",
                        "Sonication Investigation",
                    }
                    else "Logs"
                )
            else:
                self.view_mode.setCurrentText("Logs")
            self.view_mode.blockSignals(False)

            progress.setRange(0, 1000)
            if not self._progress_checkpoint(
                progress,
                790,
                "Preparing visible tables...",
            ):
                return

            self._populate_visible_tables(progress, 790, 925)
            if self._analysis_cancelled:
                return

            progress.setRange(0, 1000)
            if not self._progress_checkpoint(
                progress,
                930,
                "Building critical timeline...",
            ):
                return

            self._rebuild_timeline_only(progress, 930, 985)
            if self._analysis_cancelled:
                return

            self.apply_view_mode()
            self._progress_checkpoint(
                progress,
                1000,
                "Investigation analysis complete.",
            )

            sampling_note = ""
            if total_visible < total_indexed:
                sampling_note = (
                    f" Tables show {total_visible:,} representative rows "
                    f"from {total_indexed:,} indexed rows."
                )

            self.analysis_status.setText(
                f"{profile} complete. Sources: {loaded_sources}. "
                f"Indexed rows: {total_indexed:,}.{sampling_note}"
            )

            if profile == "Sonication Investigation":
                self.acquisition_dashboard.set_records(
                    self.source_records.get("ACQUISITION", [])
                )
                # Spectrum search uses the same files/folder/ZIP loaded by the
                # main Viewer. It runs when the Spectrum tab is opened.
                self.spectrum_analysis.explicit_paths = []
                self.sonication_console.refresh()

        finally:
            progress.close()
            self._analysis_running = False
            self.start_analysis_btn.setEnabled(True)

    def _populate_visible_tables(
        self,
        progress=None,
        start_value: int = 0,
        end_value: int = 100,
    ) -> None:
        keyword = self.search.text().strip().lower()
        source_items = list(self.tables.items())
        total_sources = max(1, len(source_items))

        for source_index, (source, table) in enumerate(source_items):
            data = [
                row
                for row in self.rows.get(source, [])
                if not keyword or keyword in row["message"].lower()
            ]

            table.setUpdatesEnabled(False)
            table.setSortingEnabled(False)
            table.setVisible(False)
            try:
                table.clearContents()
                table.setRowCount(len(data))
                table.setProperty("filtered_rows", data)

                for row_index, row in enumerate(data):
                    if row_index % 250 == 0:
                        if progress is not None:
                            fraction = (
                                source_index + row_index / max(1, len(data))
                            ) / total_sources
                            value = start_value + int(
                                (end_value - start_value) * fraction
                            )
                            if not self._progress_checkpoint(
                                progress,
                                value,
                                f"Rendering {source}: "
                                f"{row_index:,}/{len(data):,} rows",
                            ):
                                return

                    values = [
                        row["time"],
                        row["message"],
                        row["level"],
                        str(row["line"]),
                    ]
                    for column, value in enumerate(values):
                        table.setItem(
                            row_index,
                            column,
                            QTableWidgetItem(value),
                        )
            finally:
                table.setUpdatesEnabled(True)
                table.setVisible(True)

    def _rebuild_timeline_only(
        self,
        progress=None,
        start_value: int = 0,
        end_value: int = 100,
    ) -> None:
        self.timeline.clear()
        counts = {
            "critical": 0,
            "warning": 0,
            "restart": 0,
            "watchdog": 0,
            "timeout": 0,
        }
        timeline_items = []
        source_rows = list(self.rows.items())
        total_sources = max(1, len(source_rows))

        for source_index, (source, rows) in enumerate(source_rows):
            for row_index, row in enumerate(rows):
                if row_index % 500 == 0 and progress is not None:
                    fraction = (
                        source_index + row_index / max(1, len(rows))
                    ) / total_sources
                    value = start_value + int(
                        (end_value - start_value) * fraction
                    )
                    if not self._progress_checkpoint(
                        progress,
                        value,
                        f"Timeline {source}: "
                        f"{row_index:,}/{len(rows):,} rows",
                    ):
                        return

                level = row["level"].lower()
                message = row["message"].lower()

                is_critical = "critical" in level or "error" in level
                is_warning = "warning" in level or "warn" in level

                if is_critical:
                    counts["critical"] += 1
                if is_warning:
                    counts["warning"] += 1
                for key in ("restart", "watchdog", "timeout"):
                    if key in message:
                        counts[key] += 1

                show = (
                    self.show_critical.isChecked() and is_critical
                ) or (
                    self.show_warning.isChecked() and is_warning
                )

                if show and row["timestamp"] is not None:
                    timeline_items.append((
                        row["timestamp"],
                        source,
                        row,
                    ))

        timeline_items.sort(key=lambda item: item[0])
        if len(timeline_items) > self.max_timeline_items:
            timeline_items = timeline_items[-self.max_timeline_items:]

        self.timeline.setUpdatesEnabled(False)
        try:
            for _, source, row in timeline_items:
                item = QListWidgetItem(
                    f"{row['time']} [{source}] {row['message'][:140]}"
                )
                item.setData(
                    Qt.UserRole,
                    (source, row["timestamp"]),
                )
                self.timeline.addItem(item)
        finally:
            self.timeline.setUpdatesEnabled(True)

        self.summary.setText(
            f"Critical: {counts['critical']:,}   "
            f"Warning: {counts['warning']:,}   "
            f"Restart: {counts['restart']:,}   "
            f"Watchdog: {counts['watchdog']:,}   "
            f"Timeout: {counts['timeout']:,}"
        )

    def _make_pane(self, source: str) -> QWidget:
        box = QWidget(); layout = QVBoxLayout(box)
        label = QLabel(source); label.setStyleSheet("font-size:14px;font-weight:700;color:#005DAA;")
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Timestamp", "Message / State", "Level", "Line"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.setSelectionBehavior(QTableWidget.SelectRows); table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers); table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False); table.setMouseTracking(False); table.setToolTip("")
        table.itemSelectionChanged.connect(lambda s=source: self.sync_from(s))
        layout.addWidget(label); layout.addWidget(table, 1)
        self.tables[source] = table
        return box

    def apply_search(self) -> None:
        if self._analysis_running:
            return
        self._populate_visible_tables()
        self._rebuild_timeline_only()

    def sync_from(self, source: str) -> None:
        if self._syncing: return
        table = self.tables.get(source)
        if table is None: return
        selected = table.selectionModel().selectedRows()
        if not selected: return
        rows = table.property("filtered_rows") or []
        index = selected[0].row()
        if not (0 <= index < len(rows)): return
        timestamp = rows[index].get("timestamp")
        if timestamp is not None:
            self.sync_all_to_time(timestamp, source)

    def sync_all_to_time(self, timestamp: datetime, source_to_skip: str = "") -> None:
        if self._syncing: return
        self._syncing = True
        try:
            tolerance = int(self.tolerance.currentData())
            for source, table in self.tables.items():
                if source == source_to_skip: continue
                rows = table.property("filtered_rows") or []
                best_index = -1; best_diff = None
                for index, row in enumerate(rows):
                    ts = row.get("timestamp")
                    if ts is None: continue
                    diff = abs((ts - timestamp).total_seconds())
                    if best_diff is None or diff < best_diff:
                        best_diff = diff; best_index = index
                if best_index >= 0 and (tolerance == 0 and best_diff == 0 or tolerance > 0 and best_diff <= tolerance):
                    table.selectRow(best_index); table.scrollToItem(table.item(best_index, 1), QTableWidget.PositionAtCenter)
            self.chart.set_cursor_time(timestamp)
        finally:
            self._syncing = False

    def timeline_jump(self, item: QListWidgetItem) -> None:
        _source, timestamp = item.data(Qt.UserRole)
        self.sync_all_to_time(timestamp)

    def add_bookmark(self) -> None:
        for source, table in self.tables.items():
            selected = table.selectionModel().selectedRows()
            if not selected: continue
            rows = table.property("filtered_rows") or []
            index = selected[0].row()
            if 0 <= index < len(rows):
                row = rows[index]
                item = QListWidgetItem(f"{row['time']} [{source}] {row['message'][:120]}")
                item.setData(Qt.UserRole, (source, row.get("timestamp")))
                self.bookmarks.addItem(item)
                return
        QMessageBox.information(self, "Bookmark", "Select a row first.")

    def bookmark_jump(self, item: QListWidgetItem) -> None:
        _source, timestamp = item.data(Qt.UserRole)
        if timestamp is not None: self.sync_all_to_time(timestamp)

    def export_bookmarks(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Bookmarks", "investigation_bookmarks.csv", "CSV (*.csv)")
        if not path: return
        with open(path, "w", encoding="utf-8-sig", newline="") as stream:
            stream.write("bookmark\n")
            for index in range(self.bookmarks.count()):
                stream.write('"' + self.bookmarks.item(index).text().replace('"', '""') + '"\n')
