# -*- coding: utf-8 -*-
"""
VIMeasure Analyzer Ver7.0
Reads VIMeasure HW MEASURE DATA text files and displays voltage/current charts.
Python 3.13 / PySide6 / Nuitka compatible.
"""
from __future__ import annotations

import csv
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, Qt, QEvent, QTimer
from PySide6.QtGui import QAction, QColor, QPainter, QCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QComboBox,
    QToolTip,
)
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

APP_TITLE = "VIMeasure Analyzer Ver7.0"
MAX_DRAW_POINTS_PER_SERIES = 6000
TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}):(\d{3})\s+(.+)$")
DATA_HEADER_RE = re.compile(r"^;\s*Data:\s*(.+)$", re.IGNORECASE)
FILENAME_DATE_RE = re.compile(
    r"VIMeasure_([A-Za-z]{3})_([A-Za-z]{3})_(\d{1,2})_(\d{1,2})_(\d{1,2})_(\d{1,2})_(\d{4})",
    re.IGNORECASE,
)
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

COLOR_LIST = [
    "#E53935", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#00ACC1", "#FDD835",
    "#6D4C41", "#3949AB", "#7CB342", "#D81B60", "#00897B", "#C0CA33", "#5E35B1",
]

@dataclass
class MeasureData:
    path: Path
    labels: List[str]
    x_seconds: List[float]
    values: Dict[str, List[float]]
    start_datetime: Optional[datetime]

    @property
    def row_count(self) -> int:
        return len(self.x_seconds)

    @property
    def duration_seconds(self) -> float:
        if not self.x_seconds:
            return 0.0
        return self.x_seconds[-1] - self.x_seconds[0]


def parse_datetime_from_filename(path: Path) -> Optional[datetime]:
    m = FILENAME_DATE_RE.search(path.name)
    if not m:
        return None
    _, mon, day, hh, mm, ss, year = m.groups()
    month = MONTHS.get(mon.title())
    if not month:
        return None
    try:
        return datetime(int(year), month, int(day), int(hh), int(mm), int(ss))
    except ValueError:
        return None


def parse_time_to_seconds(hh: str, mm: str, ss: str, ms: str) -> float:
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def read_measure_file(path: Path) -> MeasureData:
    labels: Optional[List[str]] = None
    raw_times: List[float] = []
    rows: List[List[float]] = []

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            line = line.rstrip("\r\n")
            if labels is None:
                hm = DATA_HEADER_RE.match(line)
                if hm:
                    labels = hm.group(1).split()
                continue
            m = TIME_RE.match(line)
            if not m:
                continue
            tsec = parse_time_to_seconds(m.group(1), m.group(2), m.group(3), m.group(4))
            parts = m.group(5).split()
            if len(parts) < len(labels):
                parts += ["nan"] * (len(labels) - len(parts))
            vals: List[float] = []
            for s in parts[: len(labels)]:
                try:
                    vals.append(float(s))
                except ValueError:
                    vals.append(float("nan"))
            raw_times.append(tsec)
            rows.append(vals)

    if not labels:
        raise ValueError("Data header '; Data:' was not found.")
    if not rows:
        raise ValueError("No data rows were found.")

    # DO-level reader style: use continuous elapsed time and handle midnight rollover.
    x: List[float] = []
    day_offset = 0.0
    prev: Optional[float] = None
    for t in raw_times:
        if prev is not None and t + day_offset < prev - 12 * 3600:
            day_offset += 24 * 3600
        cont = t + day_offset
        x.append(cont)
        prev = cont
    base = x[0]
    x_elapsed = [v - base for v in x]

    values: Dict[str, List[float]] = {lab: [] for lab in labels}
    for row in rows:
        for lab, val in zip(labels, row):
            values[lab].append(val)

    file_dt = parse_datetime_from_filename(path)
    return MeasureData(path=path, labels=labels, x_seconds=x_elapsed, values=values, start_datetime=file_dt)


def is_measure_file(path: Path) -> bool:
    """Content-based VIMeasure detection; filenames are intentionally ignored."""
    if not path.is_file() or path.suffix.lower() not in {".txt", ".log", ".dat"}:
        return False
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            header_found = False
            for index, line in enumerate(stream):
                if index > 400:
                    break
                text = line.rstrip("\r\n")
                if not header_found:
                    header_found = DATA_HEADER_RE.match(text) is not None
                    continue
                if TIME_RE.match(text):
                    return True
    except OSError:
        return False
    return False

def collect_files_from_folder(folder: Path) -> List[Path]:
    files = [p for p in folder.rglob("*") if is_measure_file(p)]
    return sorted(files, key=lambda p: parse_datetime_from_filename(p) or datetime.fromtimestamp(p.stat().st_mtime))


def downsample_xy(x: List[float], y: List[float], max_points: int = MAX_DRAW_POINTS_PER_SERIES) -> Tuple[List[float], List[float]]:
    n = len(x)
    if n <= max_points:
        return x, y
    step = max(1, math.ceil(n / max_points))
    return x[::step], y[::step]


def nice_range(vmin: float, vmax: float) -> Tuple[float, float]:
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        return 0.0, 1.0
    if abs(vmax - vmin) < 1e-9:
        pad = max(abs(vmax) * 0.1, 1.0)
        return vmin - pad, vmax + pad
    pad = (vmax - vmin) * 0.08
    return vmin - pad, vmax + pad


def is_current_series(label: str) -> bool:
    return label.lower().endswith("i")


def is_voltage_series(label: str) -> bool:
    return label.lower().endswith("v")


class ZoomChartView(QChartView):
    """QChartView with click-drag zoom, right-click zoom out, and double-click reset."""
    def __init__(self, chart: QChart, parent=None) -> None:
        super().__init__(chart, parent)
        # PySide6 changed some enum access names between versions.
        # This compatibility block prevents a silent startup crash in the EXE.
        try:
            rubber_band = QChartView.RectangleRubberBand
        except AttributeError:
            rubber_band = QChartView.RubberBand.RectangleRubberBand
        self.setRubberBand(rubber_band)
        self._home_ranges = None

    def set_home_ranges(self, x_range, y_left_range, y_right_range=None) -> None:
        self._home_ranges = (x_range, y_left_range, y_right_range)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.RightButton:
            self.chart().zoom(0.5)
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if self._home_ranges:
            chart = self.chart()
            axes_h = chart.axes(Qt.Horizontal)
            axes_v = chart.axes(Qt.Vertical)
            if axes_h:
                axes_h[0].setRange(*self._home_ranges[0])
            if axes_v:
                # Axis order is stable in this app: left first, right second when visible.
                axes_v[0].setRange(*self._home_ranges[1])
                if len(axes_v) > 1 and self._home_ranges[2]:
                    axes_v[1].setRange(*self._home_ranges[2])
        else:
            self.chart().zoomReset()
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1300, 850)
        self.files: List[Path] = []
        self.current_index = -1
        self.data: Optional[MeasureData] = None
        self.checks: Dict[str, QCheckBox] = {}
        self.series_map: Dict[str, QLineSeries] = {}
        self.group_check_updating = False

        self.chart = QChart()
        self.chart.setTitle("VIMeasure Chart")
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart_view = ZoomChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()
        self.axis_y2 = QValueAxis()
        self.axis_x.setTitleText("Elapsed time (min)")
        self.axis_y.setTitleText("Voltage / selected value")
        self.axis_y2.setTitleText("Current")
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.chart.addAxis(self.axis_y2, Qt.AlignRight)
        self.axis_y2.setVisible(False)

        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(520)
        self.file_combo.currentIndexChanged.connect(self.on_combo_changed)
        self.status_label = QLabel("Ready")
        self.visible_label = QLabel("Visible: 0 / 0")
        self.summary = QTableWidget(0, 4)
        self.summary.setHorizontalHeaderLabels(["Series", "Min", "Max", "Average"])
        self.summary.setMinimumHeight(135)

        self.build_ui()
        self.build_menu()

    def build_menu(self) -> None:
        menu = self.menuBar().addMenu("File")
        a_open = QAction("Import File", self)
        a_open.triggered.connect(self.import_file)
        a_folder = QAction("Import Folder", self)
        a_folder.triggered.connect(self.import_folder)
        a_csv = QAction("Export Current CSV", self)
        a_csv.triggered.connect(self.export_csv)
        menu.addAction(a_open)
        menu.addAction(a_folder)
        menu.addSeparator()
        menu.addAction(a_csv)

    def build_ui(self) -> None:
        top = QWidget()
        main = QVBoxLayout(top)

        toolbar = QHBoxLayout()
        btn_file = QPushButton("Import File")
        btn_file.clicked.connect(self.import_file)
        btn_folder = QPushButton("Import Folder")
        btn_folder.clicked.connect(self.import_folder)
        btn_prev = QPushButton("P")
        btn_prev.setToolTip("Previous file")
        btn_prev.clicked.connect(self.prev_file)
        btn_next = QPushButton("N")
        btn_next.setToolTip("Next file")
        btn_next.clicked.connect(self.next_file)
        self.cb_data_all = QCheckBox("Data All")
        self.cb_v_all = QCheckBox("V All")
        self.cb_i_all = QCheckBox("I All")
        for cb in (self.cb_data_all, self.cb_v_all, self.cb_i_all):
            cb.setTristate(True)
        self.cb_data_all.clicked.connect(lambda checked: self.apply_group_check("all", checked))
        self.cb_v_all.clicked.connect(lambda checked: self.apply_group_check("v", checked))
        self.cb_i_all.clicked.connect(lambda checked: self.apply_group_check("i", checked))
        btn_zoom_out = QPushButton("Zoom Out")
        btn_zoom_out.clicked.connect(lambda: self.chart.zoom(0.5))
        btn_reset_zoom = QPushButton("Reset Zoom")
        btn_reset_zoom.clicked.connect(self.reset_zoom)
        btn_default = QPushButton("Default")
        btn_default.clicked.connect(self.select_default_series)
        toolbar.addWidget(btn_file)
        toolbar.addWidget(btn_folder)
        toolbar.addWidget(btn_prev)
        toolbar.addWidget(self.file_combo, 1)
        toolbar.addWidget(btn_next)
        main.addLayout(toolbar)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.chart_view)

        lower = QFrame()
        lower_outer = QVBoxLayout(lower)
        lower_layout = QHBoxLayout()
        group = QGroupBox("Series")
        self.series_layout = QGridLayout(group)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(group)
        lower_layout.addWidget(scroll, 2)
        lower_layout.addWidget(self.summary, 3)
        lower_outer.addLayout(lower_layout, 1)

        group_controls = QHBoxLayout()
        group_controls.addWidget(self.visible_label)
        group_controls.addStretch(1)
        group_controls.addWidget(self.cb_data_all)
        group_controls.addWidget(self.cb_v_all)
        group_controls.addWidget(self.cb_i_all)
        group_controls.addStretch(1)
        group_controls.addWidget(btn_default)
        group_controls.addWidget(btn_zoom_out)
        group_controls.addWidget(btn_reset_zoom)
        lower_outer.addLayout(group_controls)
        splitter.addWidget(lower)
        splitter.setSizes([640, 180])
        main.addWidget(splitter, 1)
        main.addWidget(self.status_label)
        self.setCentralWidget(top)

    def import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select VIMeasure file", "", "Text/Log Files (*.txt *.log);;All Files (*.*)")
        if path:
            self.files = [Path(path)]
            self.load_index(0)

    def import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder containing VIMeasure files", "")
        if not folder:
            return
        files = collect_files_from_folder(Path(folder))
        if not files:
            QMessageBox.warning(self, APP_TITLE, "No VIMeasure .txt/.log files were found in the selected folder.")
            return
        self.files = files
        self.load_index(len(files) - 1)  # default latest in sorted order

    def load_index(self, idx: int) -> None:
        if not (0 <= idx < len(self.files)):
            return
        try:
            self.data = read_measure_file(self.files[idx])
        except Exception as e:
            QMessageBox.critical(self, APP_TITLE, f"Failed to read file:\n{self.files[idx]}\n\n{e}")
            return
        self.current_index = idx
        self.refresh_combo()
        self.create_series_controls()
        self.select_default_series()
        self.status_label.setText(f"Loaded {self.files[idx].name} | rows={self.data.row_count:,} | duration={self.data.duration_seconds/60:.2f} min")

    def refresh_combo(self) -> None:
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        for p in self.files:
            self.file_combo.addItem(str(p))
        self.file_combo.setCurrentIndex(self.current_index)
        self.file_combo.blockSignals(False)

    def on_combo_changed(self, idx: int) -> None:
        if idx != self.current_index and 0 <= idx < len(self.files):
            self.load_index(idx)

    def prev_file(self) -> None:
        if self.files:
            self.load_index(max(0, self.current_index - 1))

    def next_file(self) -> None:
        if self.files:
            self.load_index(min(len(self.files) - 1, self.current_index + 1))

    def create_series_controls(self) -> None:
        while self.series_layout.count():
            item = self.series_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.checks.clear()
        if not self.data:
            return
        for i, lab in enumerate(self.data.labels):
            cb = QCheckBox(lab)
            cb.stateChanged.connect(self.on_series_check_changed)
            self.checks[lab] = cb
            self.series_layout.addWidget(cb, i // 2, i % 2)

    def set_all_checks(self, checked: bool) -> None:
        self.group_check_updating = True
        for cb in self.checks.values():
            cb.setChecked(checked)
        self.group_check_updating = False
        self.update_group_checks()
        self.update_chart()

    def apply_group_check(self, group: str, checked: bool) -> None:
        if self.group_check_updating:
            return
        self.group_check_updating = True
        for lab, cb in self.checks.items():
            if group == "all" or (group == "v" and is_voltage_series(lab)) or (group == "i" and is_current_series(lab)):
                cb.setChecked(checked)
        self.group_check_updating = False
        self.update_group_checks()
        self.update_chart()

    def on_series_check_changed(self) -> None:
        if not self.group_check_updating:
            self.update_group_checks()
            self.update_chart()

    def update_group_checks(self) -> None:
        if not hasattr(self, "cb_data_all"):
            return
        self.group_check_updating = True
        def set_tri(cb: QCheckBox, items: List[QCheckBox]) -> None:
            cb.blockSignals(True)
            if not items:
                cb.setCheckState(Qt.Unchecked)
            elif all(x.isChecked() for x in items):
                cb.setCheckState(Qt.Checked)
            elif any(x.isChecked() for x in items):
                cb.setCheckState(Qt.PartiallyChecked)
            else:
                cb.setCheckState(Qt.Unchecked)
            cb.blockSignals(False)
        all_items = list(self.checks.values())
        v_items = [cb for lab, cb in self.checks.items() if is_voltage_series(lab)]
        i_items = [cb for lab, cb in self.checks.items() if is_current_series(lab)]
        set_tri(self.cb_data_all, all_items)
        set_tri(self.cb_v_all, v_items)
        set_tri(self.cb_i_all, i_items)
        visible = sum(1 for cb in all_items if cb.isChecked())
        self.visible_label.setText(f"Visible: {visible} / {len(all_items)}")
        self.group_check_updating = False

    def select_default_series(self) -> None:
        # Default shows the practical voltage rails and 48V rails, keeping current spikes optional.
        preferred = {"4vV", "-6vV", "6vV", "FE_48vV", "ER_48vV", "-15vV", "15vV"}
        for lab, cb in self.checks.items():
            cb.blockSignals(True)
            cb.setChecked(lab in preferred)
            cb.blockSignals(False)
        self.update_group_checks()
        self.update_chart()

    def update_chart(self) -> None:
        if not self.data:
            return
        self.chart.removeAllSeries()
        self.series_map.clear()
        selected = [lab for lab, cb in self.checks.items() if cb.isChecked()]
        selected_v = [lab for lab in selected if is_voltage_series(lab)]
        selected_i = [lab for lab in selected if is_current_series(lab)]
        use_second_axis = bool(selected_v and selected_i)

        y_left_min, y_left_max = float("inf"), float("-inf")
        y_right_min, y_right_max = float("inf"), float("-inf")
        xmin, xmax = 0.0, max(1.0, self.data.duration_seconds / 60.0)

        for idx, lab in enumerate(selected):
            series = QLineSeries()
            series.setName(lab)
            color = QColor(COLOR_LIST[idx % len(COLOR_LIST)])
            series.setColor(color)
            x, y = downsample_xy(self.data.x_seconds, self.data.values[lab])
            for xx, yy in zip(x, y):
                if math.isfinite(yy):
                    x_min = xx / 60.0
                    series.append(QPointF(x_min, yy))
                    if use_second_axis and is_current_series(lab):
                        y_right_min = min(y_right_min, yy)
                        y_right_max = max(y_right_max, yy)
                    else:
                        y_left_min = min(y_left_min, yy)
                        y_left_max = max(y_left_max, yy)
            series.hovered.connect(lambda point, state, name=lab: self.show_point_tooltip(name, point, state))
            self.chart.addSeries(series)
            series.attachAxis(self.axis_x)
            if use_second_axis and is_current_series(lab):
                series.attachAxis(self.axis_y2)
            else:
                series.attachAxis(self.axis_y)
            self.series_map[lab] = series

        # Left axis is V when V and I are mixed. If only I is selected, I uses the left axis.
        y1, y2 = nice_range(y_left_min, y_left_max) if y_left_min != float("inf") else (0.0, 1.0)
        r1, r2 = nice_range(y_right_min, y_right_max) if y_right_min != float("inf") else (0.0, 1.0)
        self.axis_x.setRange(xmin, xmax)
        self.axis_x.setTickCount(8)
        self.axis_y.setRange(y1, y2)
        self.axis_y.setTickCount(8)
        self.axis_y2.setRange(r1, r2)
        self.axis_y2.setTickCount(8)
        self.axis_y2.setVisible(use_second_axis)
        self.axis_y.setTitleText("Voltage" if use_second_axis else "Selected value")
        self.axis_y2.setTitleText("Current")
        if hasattr(self.chart_view, "set_home_ranges"):
            self.chart_view.set_home_ranges((xmin, xmax), (y1, y2), (r1, r2) if use_second_axis else None)
        title = f"VIMeasure Chart - {self.data.path.name}"
        if self.data.start_datetime:
            title += f" ({self.data.start_datetime:%Y-%m-%d %H:%M:%S})"
        if use_second_axis:
            title += " | V=left axis, I=right axis"
        self.chart.setTitle(title)
        self.update_summary(selected)

    def reset_zoom(self) -> None:
        if hasattr(self.chart_view, "_home_ranges") and self.chart_view._home_ranges:
            x_rng, y_rng, r_rng = self.chart_view._home_ranges
            self.axis_x.setRange(*x_rng)
            self.axis_y.setRange(*y_rng)
            if r_rng:
                self.axis_y2.setRange(*r_rng)
        else:
            self.chart.zoomReset()

    def show_point_tooltip(self, name: str, point: QPointF, state: bool) -> None:
        if state:
            QToolTip.showText(
                QCursor.pos(),
                f"{name}\nTime: {point.x():.3f} min\nValue: {point.y():.4g}",
                self.chart_view,
            )
        else:
            QToolTip.hideText()

    def update_summary(self, selected: List[str]) -> None:
        self.summary.setRowCount(len(selected))
        if not self.data:
            return
        for r, lab in enumerate(selected):
            vals = [v for v in self.data.values[lab] if math.isfinite(v)]
            self.summary.setItem(r, 0, QTableWidgetItem(lab))
            if vals:
                avg = sum(vals) / len(vals)
                items = [min(vals), max(vals), avg]
                for c, val in enumerate(items, 1):
                    self.summary.setItem(r, c, QTableWidgetItem(f"{val:.4g}"))
            else:
                for c in range(1, 4):
                    self.summary.setItem(r, c, QTableWidgetItem(""))
        self.summary.resizeColumnsToContents()

    def export_csv(self) -> None:
        if not self.data:
            QMessageBox.information(self, APP_TITLE, "No file is loaded.")
            return
        default = self.data.path.with_suffix(".csv").name
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", default, "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["ElapsedSeconds"] + self.data.labels)
            for i, x in enumerate(self.data.x_seconds):
                w.writerow([f"{x:.3f}"] + [self.data.values[lab][i] for lab in self.data.labels])
        self.status_label.setText(f"CSV exported: {path}")


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def write_crash_log(exc: BaseException) -> None:
    import traceback
    log_path = app_base_dir() / "VIMeasureAnalyzer_error.log"
    try:
        with log_path.open("w", encoding="utf-8") as f:
            f.write(f"{APP_TITLE} startup/runtime error\n")
            f.write("=" * 60 + "\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
    except Exception:
        pass


def main() -> None:
    app: Optional[QApplication] = None
    try:
        from insightec_handoff import load_handoff
        handoff = load_handoff("vimeasure")
        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        if handoff and handoff.auto_load:
            candidates = [path for path in handoff.input_paths() if path.is_file()]
            files = [path for path in candidates if is_measure_file(path)]
            if handoff.workspace():
                files.extend(collect_files_from_folder(handoff.workspace()))
            files = sorted(set(files), key=lambda path: (path.stat().st_mtime, str(path)))
            handoff.mark("vimeasure", "accepted" if files else "no-compatible-input", input_count=len(files), candidate_count=len(candidates))
            if files:
                win.files = files
                QTimer.singleShot(0, lambda: win.load_index(len(win.files) - 1))
            else:
                win.status_label.setText("Hub handoff: no compatible VIMeasure data header was found.")
        if os.environ.get("VIMEASURE_STARTUP_SMOKE_TEST") == "1":
            QTimer.singleShot(1200, app.quit)
        exit_code = app.exec()
        # Normal close returns 0. Do not route it through the crash handler.
        return
    except SystemExit as exc:
        # sys.exit(0) / normal Qt shutdown must not be treated as a startup failure.
        code = exc.code
        if code in (None, 0):
            return
        write_crash_log(exc)
        try:
            app = QApplication.instance() or app or QApplication(sys.argv)
            QMessageBox.critical(None, APP_TITLE, f"Runtime failed.\n\nExit code: {code}\n\nSee VIMeasureAnalyzer_error.log next to the EXE.")
        except Exception:
            pass
        raise
    except Exception as exc:
        write_crash_log(exc)
        try:
            app = QApplication.instance() or app or QApplication(sys.argv)
            QMessageBox.critical(None, APP_TITLE, f"Startup failed.\n\n{exc}\n\nSee VIMeasureAnalyzer_error.log next to the EXE.")
        except Exception:
            pass
        raise

if __name__ == "__main__":
    main()
