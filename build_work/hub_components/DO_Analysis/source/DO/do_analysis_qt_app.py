# -*- coding: utf-8 -*-
"""
DO Analysis Qt Windows App
Python 3.13 / PySide6 / Nuitka friendly
No pandas, no matplotlib, no QtCharts.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import statistics
import sys
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from PySide6.QtCore import Qt, QRectF, QPointF, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QPainter, QPen, QColor, QFont, QBrush
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QFileDialog, QLabel, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QLineEdit, QCheckBox, QDoubleSpinBox, QSpinBox,
    QMessageBox, QProgressBar, QSplitter, QGroupBox, QComboBox
)

RELEASE_MODE = os.environ.get("INSIGHTEC_RELEASE_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}

from common_guide import GuideConfig, GuideManager, GuidePage

APP_NAME = "DO Analysis Qt"
APP_VERSION = "2026.07.28.7"

MIN_VALID_DO = 0.0
MAX_VALID_DO = 10.0
MIN_EVENT_DURATION_MIN = 3.0
EVENT_MERGE_GAP_MIN = 3.0
MIN_DO_CHANGE_FOR_VACUUM = 0.7
DO_AVG_BAND = 0.2
VACUUM_FLAT_TOLERANCE = 0.10
SECONDARY_FLOW_VALID_MIN = 2.0
SECONDARY_FLOW_VALID_MAX = 6.5

STATE_DEGAS = "DEGAS"
STATE_TREAT = "TREAT"
STATE_CLEAN_TANK = "CLEAN_TANK"
STATE_CLEAN_XD = "CLEAN_XD"

HEADER_RE = re.compile(r"MainState\s+CoolingState\s+Error", re.IGNORECASE)
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2}):(\d{1,3})")


def normalize_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.strip().lower())


def is_valid_do(v: float) -> bool:
    return MIN_VALID_DO <= v <= MAX_VALID_DO


def classify_state(state: str) -> Optional[str]:
    s = state.strip().upper()
    if "DEGAS" in s and "CIRCULATE" in s:
        return STATE_DEGAS
    if "TREAT" in s and "CIRCULATE" in s:
        return STATE_TREAT
    if "CLEAN" in s and "TANK" in s and "CIRCULATE" in s:
        return STATE_CLEAN_TANK
    if "CLEAN" in s and "XD" in s and "CIRCULATE" in s:
        return STATE_CLEAN_XD
    return None


def parse_time_minutes(text: str) -> Optional[float]:
    m = TIME_RE.match(text.strip())
    if not m:
        return None
    h, mi, sec, ms = [int(x) for x in m.groups()]
    return h * 60.0 + mi + sec / 60.0 + ms / 60000.0


@dataclass
class Sample:
    time_text: str
    time_min: float
    state: str
    do: Optional[float]
    vacuum: Optional[float]
    second_flow: Optional[float]
    primary_flow: Optional[float]
    chiller_temp: Optional[float]
    absolute_pressure: Optional[float]
    dynamic_pressure: Optional[float]


@dataclass
class EventResult:
    file_name: str
    event_type: str
    event_no: int
    start_time: str
    end_time: str
    duration_min: float
    max_do: Optional[float]
    min_do: Optional[float]
    do_change: Optional[float]
    high_do_vac: Optional[float]
    low_do_vac: Optional[float]
    vac_diff: Optional[float]
    vacuum_trend: str
    second_flow_avg: Optional[float]
    note: str = ""


@dataclass
class FileSummary:
    file_path: str
    file_name: str
    sample_count: int
    event_count: int
    up_count: int
    flat_count: int
    down_count: int
    na_count: int


class WaterSystemParser:
    def parse_file(self, file_path: str) -> Tuple[List[Sample], Dict[str, int]]:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        header_line = None
        header_index = -1
        for idx, line in enumerate(lines):
            if HEADER_RE.search(line):
                header_line = line
                header_index = idx
                break
        if header_line is None:
            raise ValueError("Header line was not found. Expected WaterSystem log format.")

        tokens = header_line.split()
        # First token is time, then headers begin with MainState.
        headers = [normalize_header(x) for x in tokens[1:]]
        idx_map = {h: i for i, h in enumerate(headers)}
        required = ["mainstate", "vacuumlevel", "dolevel"]
        for key in required:
            if key not in idx_map:
                raise ValueError(f"Required column not found: {key}")

        samples: List[Sample] = []
        prev_t: Optional[float] = None
        day_offset = 0.0
        for line in lines[header_index + 1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < len(headers) + 1:
                continue
            raw_t = parse_time_minutes(parts[0])
            if raw_t is None:
                continue
            t = raw_t + day_offset
            if prev_t is not None and t < prev_t - 720.0:
                day_offset += 1440.0
                t = raw_t + day_offset
            prev_t = t
            values = parts[1:]
            def get_str(key: str) -> str:
                i = idx_map.get(key, -1)
                return values[i] if 0 <= i < len(values) else ""
            def get_float(key: str) -> Optional[float]:
                v = get_str(key)
                try:
                    return float(v)
                except Exception:
                    return None
            samples.append(Sample(
                time_text=parts[0],
                time_min=t,
                state=get_str("mainstate"),
                do=get_float("dolevel"),
                vacuum=get_float("vacuumlevel"),
                second_flow=get_float("secondaryflowmeter") if "secondaryflowmeter" in idx_map else None,
                primary_flow=get_float("primaryflowmeter") if "primaryflowmeter" in idx_map else None,
                chiller_temp=get_float("chillertemp") if "chillertemp" in idx_map else None,
                absolute_pressure=get_float("absolutepressure") if "absolutepressure" in idx_map else None,
                dynamic_pressure=get_float("dynamicpressure") if "dynamicpressure" in idx_map else None,
            ))
        return samples, idx_map


class DOAnalyzer:
    def __init__(self, min_do_change: float = MIN_DO_CHANGE_FOR_VACUUM,
                 do_band: float = DO_AVG_BAND,
                 flat_tol: float = VACUUM_FLAT_TOLERANCE):
        self.min_do_change = min_do_change
        self.do_band = do_band
        self.flat_tol = flat_tol

    def analyze_file(self, file_path: str, samples: List[Sample]) -> Tuple[List[EventResult], FileSummary]:
        file_name = Path(file_path).name
        events = self._detect_events(samples)
        results: List[EventResult] = []
        counters = {STATE_DEGAS: 0, STATE_TREAT: 0, STATE_CLEAN_TANK: 0, STATE_CLEAN_XD: 0}
        for s_idx, e_idx, etype in events:
            block = samples[s_idx:e_idx + 1]
            duration = block[-1].time_min - block[0].time_min
            if duration < MIN_EVENT_DURATION_MIN:
                continue
            counters[etype] += 1
            results.append(self._analyze_event(file_name, etype, counters[etype], block))
        up = sum(1 for r in results if r.vacuum_trend == "UP")
        down = sum(1 for r in results if r.vacuum_trend == "DOWN")
        flat = sum(1 for r in results if r.vacuum_trend == "FLAT")
        na = sum(1 for r in results if r.vacuum_trend.startswith("N/A"))
        summary = FileSummary(file_path, file_name, len(samples), len(results), up, flat, down, na)
        return results, summary

    def _detect_events(self, samples: List[Sample]) -> List[Tuple[int, int, str]]:
        raw: List[Tuple[int, int, str]] = []
        in_event = False
        cur_start = 0
        cur_type = ""
        for i, smp in enumerate(samples):
            target = None
            if smp.do is not None and is_valid_do(smp.do):
                target = classify_state(smp.state)
            if target:
                if not in_event:
                    in_event = True
                    cur_start = i
                    cur_type = target
                elif target != cur_type:
                    raw.append((cur_start, i - 1, cur_type))
                    cur_start = i
                    cur_type = target
            else:
                if in_event:
                    raw.append((cur_start, i - 1, cur_type))
                    in_event = False
        if in_event:
            raw.append((cur_start, len(samples) - 1, cur_type))

        if not raw:
            return []
        merged = [raw[0]]
        for s, e, typ in raw[1:]:
            ps, pe, ptyp = merged[-1]
            gap = samples[s].time_min - samples[pe].time_min
            if typ == ptyp and gap <= EVENT_MERGE_GAP_MIN:
                merged[-1] = (ps, e, ptyp)
            else:
                merged.append((s, e, typ))
        return merged

    def _analyze_event(self, file_name: str, etype: str, event_no: int, block: List[Sample]) -> EventResult:
        do_vals = [s.do for s in block if s.do is not None and is_valid_do(s.do)]
        max_do = max(do_vals) if do_vals else None
        min_do = min(do_vals) if do_vals else None
        do_change = (max_do - min_do) if max_do is not None and min_do is not None else None
        high_vac = low_vac = diff = None
        trend = "N/A"
        note = ""
        if etype in (STATE_CLEAN_TANK, STATE_CLEAN_XD):
            trend = "N/A Clean"
            note = "Clean event: vacuum trend is not judged."
        elif do_change is None:
            trend = "N/A No DO"
        elif do_change < self.min_do_change:
            trend = "N/A DO Change"
            note = f"DO change {do_change:.2f} ppm < {self.min_do_change:.2f} ppm"
        else:
            high_vacs = [s.vacuum for s in block if s.do is not None and s.vacuum is not None and s.do >= max_do - self.do_band]
            low_vacs = [s.vacuum for s in block if s.do is not None and s.vacuum is not None and s.do <= min_do + self.do_band]
            if not high_vacs or not low_vacs:
                trend = "N/A No Vacuum"
            else:
                high_vac = statistics.fmean(high_vacs)
                low_vac = statistics.fmean(low_vacs)
                diff = low_vac - high_vac
                if diff > self.flat_tol:
                    trend = "UP"
                elif diff < -self.flat_tol:
                    trend = "DOWN"
                else:
                    trend = "FLAT"
        sf_vals = [s.second_flow for s in block if s.second_flow is not None and SECONDARY_FLOW_VALID_MIN <= s.second_flow <= SECONDARY_FLOW_VALID_MAX]
        sf_avg = statistics.fmean(sf_vals) if sf_vals else None
        return EventResult(
            file_name=file_name, event_type=etype, event_no=event_no,
            start_time=block[0].time_text, end_time=block[-1].time_text,
            duration_min=max(0.0, block[-1].time_min - block[0].time_min),
            max_do=max_do, min_do=min_do, do_change=do_change,
            high_do_vac=high_vac, low_do_vac=low_vac, vac_diff=diff,
            vacuum_trend=trend, second_flow_avg=sf_avg, note=note
        )


class AnalyzeWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(list, list, str)
    failed = Signal(str)
    def __init__(self, files: List[str], min_do_change: float, do_band: float, flat_tol: float):
        super().__init__()
        self.files = files
        self.min_do_change = min_do_change
        self.do_band = do_band
        self.flat_tol = flat_tol
    def run(self) -> None:
        try:
            parser = WaterSystemParser()
            analyzer = DOAnalyzer(self.min_do_change, self.do_band, self.flat_tol)
            all_results: List[EventResult] = []
            summaries: List[FileSummary] = []
            errors = []
            total = max(1, len(self.files))
            for idx, f in enumerate(self.files, start=1):
                self.progress.emit(int((idx - 1) / total * 100), Path(f).name)
                try:
                    samples, _ = parser.parse_file(f)
                    results, summary = analyzer.analyze_file(f, samples)
                    all_results.extend(results)
                    summaries.append(summary)
                except Exception as exc:
                    errors.append(f"{Path(f).name}: {exc}")
            self.progress.emit(100, "Completed")
            self.finished.emit(all_results, summaries, "\n".join(errors))
        except Exception as exc:
            self.failed.emit(str(exc))


class ChartWidget(QWidget):
    zoomSelected = Signal(float, float)
    rangeSelected = Signal(float, float)

    """Native Qt chart with file title, hover crosshair and value readout.

    This intentionally avoids matplotlib/QtCharts so the application remains
    Nuitka/Python 3.13 friendly.  The chart supports the practical functions
    needed for log review: DO/Vacuum/2nd Flow overlay, hover value inspection,
    file switching from the Chart tab, and event start/end markers.
    """
    def __init__(self) -> None:
        super().__init__()
        self.samples: List[Sample] = []
        self.events: List[EventResult] = []
        self.file_name: str = ""
        self.show_do = True
        self.show_vac = True
        self.show_sf = True
        self.show_primary_flow = False
        self.show_chiller_temp = False
        self.show_absolute_pressure = False
        self.show_dynamic_pressure = False
        self.show_event_markers = True
        self.show_non_event_labels = False
        self.show_value_popup = True
        self.range_analysis_enabled = False
        self.range_parameter = "DO Level"
        self.range_selection: Optional[Tuple[float, float]] = None
        self.range_result: Optional[Dict[str, Any]] = None
        self.show_range_overlay = True
        self.x_min_override: Optional[float] = None
        self.x_max_override: Optional[float] = None
        self._mouse_pos: Optional[QPointF] = None
        self._drag_start: Optional[QPointF] = None
        self._drag_current: Optional[QPointF] = None
        self._is_dragging = False
        self._plot_rect = QRectF()
        self.setMouseTracking(True)
        self.setMinimumHeight(360)

    def set_samples(self, samples: List[Sample], file_name: str = "", events: Optional[List[EventResult]] = None) -> None:
        self.samples = samples
        self.file_name = file_name
        self.events = events or []
        self.x_min_override = None
        self.x_max_override = None
        self.clear_range_analysis()
        self.update()

    def set_range_analysis(self, enabled: bool, parameter: str, show_overlay: bool = True) -> None:
        self.range_analysis_enabled = enabled
        self.range_parameter = parameter
        self.show_range_overlay = show_overlay
        if not enabled:
            self._is_dragging = False
            self._drag_start = None
            self._drag_current = None
        self.update()

    def set_range_result(self, start: float, end: float, result: Dict[str, Any]) -> None:
        self.range_selection = (start, end)
        self.range_result = dict(result)
        self.update()

    def clear_range_analysis(self) -> None:
        self.range_selection = None
        self.range_result = None
        self.update()

    def set_zoom_range(self, xmin: Optional[float], xmax: Optional[float]) -> None:
        if xmin is None or xmax is None or xmax <= xmin:
            self.x_min_override = None
            self.x_max_override = None
        else:
            self.x_min_override = xmin
            self.x_max_override = xmax
        self.update()

    def reset_zoom(self) -> None:
        self.x_min_override = None
        self.x_max_override = None
        self.update()


    def _plot_x_to_time(self, px: float) -> Optional[float]:
        if not self.samples or self._plot_rect.width() <= 0:
            return None
        xmin, xmax = self._time_range()
        x = max(self._plot_rect.left(), min(px, self._plot_rect.right()))
        return xmin + (x - self._plot_rect.left()) / self._plot_rect.width() * (xmax - xmin)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        pos = QPointF(event.position())
        if event.button() == Qt.LeftButton and self._plot_rect.contains(pos) and self.samples:
            self._drag_start = pos
            self._drag_current = pos
            self._is_dragging = True
            self._mouse_pos = pos
            self.update()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        pos = QPointF(event.position())
        if event.button() == Qt.LeftButton and self._is_dragging and self._drag_start is not None:
            t1 = self._plot_x_to_time(self._drag_start.x())
            t2 = self._plot_x_to_time(pos.x())
            self._is_dragging = False
            self._drag_current = None
            start = self._drag_start
            self._drag_start = None
            if t1 is not None and t2 is not None and abs(pos.x() - start.x()) >= 8:
                xmin, xmax = (t1, t2) if t1 <= t2 else (t2, t1)
                if self.range_analysis_enabled:
                    self.rangeSelected.emit(xmin, xmax)
                else:
                    self.set_zoom_range(xmin, xmax)
                    self.zoomSelected.emit(xmin, xmax)
            self.update()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._mouse_pos = None
        self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        pos = QPointF(event.position())
        self._mouse_pos = pos
        if self._is_dragging:
            # Keep the drag end inside the plot horizontally so the selected range is clear.
            x = max(self._plot_rect.left(), min(pos.x(), self._plot_rect.right())) if self._plot_rect.width() > 0 else pos.x()
            y = max(self._plot_rect.top(), min(pos.y(), self._plot_rect.bottom())) if self._plot_rect.height() > 0 else pos.y()
            self._drag_current = QPointF(x, y)
        self.update()

    def _time_range(self) -> Tuple[float, float]:
        xs = [s.time_min for s in self.samples]
        if not xs:
            return 0.0, 1.0
        data_min, data_max = min(xs), max(xs)
        xmin = self.x_min_override if self.x_min_override is not None else data_min
        xmax = self.x_max_override if self.x_max_override is not None else data_max
        xmin = max(data_min, xmin)
        xmax = min(data_max, xmax)
        if xmax <= xmin:
            xmin, xmax = data_min, data_max
        if xmax <= xmin:
            xmax = xmin + 1.0
        return xmin, xmax

    def _primary_range(self) -> Tuple[float, float]:
        xmin, xmax = self._time_range()
        visible = [s for s in self.samples if xmin <= s.time_min <= xmax]
        do_vals = [s.do for s in visible if s.do is not None and is_valid_do(s.do)] if self.show_do else []
        sf_vals = [s.second_flow for s in visible if s.second_flow is not None and SECONDARY_FLOW_VALID_MIN <= s.second_flow <= SECONDARY_FLOW_VALID_MAX] if self.show_sf else []
        pf_vals = [s.primary_flow for s in visible if s.primary_flow is not None] if self.show_primary_flow else []
        ct_vals = [s.chiller_temp for s in visible if s.chiller_temp is not None] if self.show_chiller_temp else []
        ap_vals = [s.absolute_pressure for s in visible if s.absolute_pressure is not None] if self.show_absolute_pressure else []
        dp_vals = [s.dynamic_pressure for s in visible if s.dynamic_pressure is not None] if self.show_dynamic_pressure else []
        values = do_vals + sf_vals + pf_vals + ct_vals + ap_vals + dp_vals
        if not values:
            return 0.0, 10.0
        ymin, ymax = min(values), max(values)
        if ymax <= ymin:
            return ymin - 1.0, ymax + 1.0
        pad = max(0.2, (ymax - ymin) * 0.12)
        return ymin - pad, ymax + pad

    def _vacuum_range(self) -> Tuple[float, float]:
        xmin, xmax = self._time_range()
        vac_vals = [s.vacuum for s in self.samples if s.vacuum is not None and xmin <= s.time_min <= xmax]
        if not vac_vals:
            return 85.0, 100.0
        vmin, vmax = min(vac_vals), max(vac_vals)
        pad = max(1.0, (vmax - vmin) * 0.08)
        return vmin - pad, vmax + pad

    def _format_minutes_as_time(self, minutes: float) -> str:
        total_ms = int(round((minutes % 1440.0) * 60000.0))
        h = total_ms // 3600000
        rem = total_ms % 3600000
        m = rem // 60000
        rem %= 60000
        sec = rem // 1000
        ms = rem % 1000
        return f"{h:02d}:{m:02d}:{sec:02d}.{ms:03d}"

    def _map_x(self, x: float, plot: QRectF, xmin: float, xmax: float) -> float:
        return plot.left() + (x - xmin) / (xmax - xmin) * plot.width()

    def _map_y(self, y: float, plot: QRectF, ymin: float, ymax: float) -> float:
        return plot.bottom() - (y - ymin) / (ymax - ymin) * plot.height()

    def _nearest_sample(self, t: float) -> Optional[Sample]:
        if not self.samples:
            return None
        # Linear scan is acceptable after decimation-free native drawing for typical log sizes.
        # It also avoids additional compiled dependencies.
        return min(self.samples, key=lambda s: abs(s.time_min - t))

    def _draw_line_series(self, p: QPainter, plot: QRectF, values: List[Tuple[float, float]],
                          xmin: float, xmax: float, ymin: float, ymax: float,
                          color: QColor, width: float = 1.4) -> None:
        if len(values) < 2 or ymax <= ymin or xmax <= xmin:
            return
        p.setPen(QPen(color, width))
        # Decimate by pixel column for speed while preserving shape.
        max_points = max(400, int(plot.width() * 2))
        step = max(1, len(values) // max_points)
        last: Optional[QPointF] = None
        for x, y in values[::step]:
            px = self._map_x(x, plot, xmin, xmax)
            py = self._map_y(y, plot, ymin, ymax)
            pt = QPointF(px, py)
            if last is not None:
                p.drawLine(last, pt)
            last = pt

    def _draw_axes(self, p: QPainter, plot: QRectF, xmin: float, xmax: float,
                   pymin: float, pymax: float, vymin: float, vymax: float) -> None:
        p.setPen(QPen(QColor(215, 215, 215), 1))
        p.drawRect(plot)
        font = QFont(); font.setPointSize(8); p.setFont(font)
        # Horizontal grid and primary labels
        for i in range(6):
            y = plot.top() + plot.height() * i / 5
            p.setPen(QPen(QColor(235, 235, 235), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            pv = pymax - (pymax - pymin) * i / 5
            vv = vymax - (vymax - vymin) * i / 5
            p.setPen(QColor(80, 80, 80))
            p.drawText(4, int(y + 4), f"{pv:.1f}")
            p.drawText(int(plot.right() + 8), int(y + 4), f"{vv:.1f}")
        # Vertical grid and time labels
        for i in range(6):
            x = plot.left() + plot.width() * i / 5
            p.setPen(QPen(QColor(240, 240, 240), 1))
            p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            tv = xmin + (xmax - xmin) * i / 5
            p.setPen(QColor(80, 80, 80))
            p.drawText(int(x - 34), int(plot.bottom() + 18), self._format_minutes_as_time(tv))
        p.setPen(QColor(50, 50, 50))
        p.drawText(4, int(plot.top() - 8), "Primary axis")
        p.drawText(int(plot.right() - 84), int(plot.top() - 8), "Vacuum axis")

    def _short_non_event_label(self, state: str) -> str:
        s = state.strip().upper()
        if not s:
            return "NO STATE"
        if "ERROR" in s:
            return "ERROR"
        if "DEGAS" in s and "PAUSE" in s:
            return "DEGAS PAUSE"
        if "TREAT" in s and "PAUSE" in s:
            return "TREATMENT PAUSE"
        if "INITIAL" in s:
            return "INIT"
        if "WAIT" in s:
            return "WAIT"
        if "DRAIN" in s:
            return "DRAIN"
        if "FILL" in s:
            return "FILL"
        if "CLEAN" in s and "PAUSE" in s:
            return "CLEAN PAUSE"
        compact = re.sub(r"[_\s]+", " ", s).strip()
        return compact[:18]

    def _draw_non_event_labels(self, p: QPainter, plot: QRectF, xmin: float, xmax: float) -> None:
        if not self.show_non_event_labels or not self.samples:
            return

        # Time ranges already occupied by analyzed events.  Non-event labels are
        # drawn only in the gaps so CIRCULATE labels remain easy to read.
        time_by_text: Dict[str, float] = {s.time_text: s.time_min for s in self.samples}
        event_ranges: List[Tuple[float, float]] = []
        for ev in self.events:
            st = time_by_text.get(ev.start_time)
            en = time_by_text.get(ev.end_time)
            if st is not None and en is not None:
                event_ranges.append((min(st, en), max(st, en)))

        def inside_event(t: float) -> bool:
            return any(st <= t <= en for st, en in event_ranges)

        blocks: List[Tuple[float, float, str]] = []
        cur_start: Optional[float] = None
        cur_end: Optional[float] = None
        cur_label = ""
        for smp in self.samples:
            t = smp.time_min
            if t < xmin or t > xmax:
                continue
            # Real Treatment/Degas pause states must remain visible even when the
            # analyzer merges the surrounding circulate blocks into one event.
            state_upper = smp.state.strip().upper()
            is_pause_state = (
                "PAUSE" in state_upper
                and ("TREAT" in state_upper or "DEGAS" in state_upper)
            )
            is_event_state = classify_state(smp.state) is not None and smp.do is not None and is_valid_do(smp.do)
            is_non_event = is_pause_state or ((not is_event_state) and (not inside_event(t)))
            if is_non_event:
                label = self._short_non_event_label(smp.state)
                if cur_start is None:
                    cur_start = t; cur_end = t; cur_label = label
                elif label == cur_label and t - (cur_end or t) <= EVENT_MERGE_GAP_MIN:
                    cur_end = t
                else:
                    blocks.append((cur_start, cur_end if cur_end is not None else cur_start, cur_label))
                    cur_start = t; cur_end = t; cur_label = label
            else:
                if cur_start is not None:
                    blocks.append((cur_start, cur_end if cur_end is not None else cur_start, cur_label))
                    cur_start = None; cur_end = None; cur_label = ""
        if cur_start is not None:
            blocks.append((cur_start, cur_end if cur_end is not None else cur_start, cur_label))

        p.setFont(QFont("Arial", 7))
        base_colors = {
            "ERROR": QColor(220, 60, 60),
            "DEGAS PAUSE": QColor(230, 150, 70),
            "TREATMENT PAUSE": QColor(70, 170, 100),
            "INIT": QColor(140, 140, 140),
            "WAIT": QColor(120, 120, 180),
            "DRAIN": QColor(90, 140, 210),
            "FILL": QColor(80, 160, 200),
            "CLEAN PAUSE": QColor(150, 110, 190),
        }
        row = 0
        for st, en, label in blocks:
            x1 = self._map_x(max(st, xmin), plot, xmin, xmax)
            x2 = self._map_x(min(en, xmax), plot, xmin, xmax)
            width = max(1.0, x2 - x1)
            # Suppress tiny labels, but keep long non-event shaded areas visible.
            if width < 14:
                continue
            color = base_colors.get(label, QColor(150, 150, 150))
            fill = QColor(color); fill.setAlpha(12)
            p.fillRect(QRectF(x1, plot.top(), width, plot.height()), fill)
            p.setPen(QPen(color, 1, Qt.DotLine))
            p.drawLine(QPointF(x1, plot.top()), QPointF(x1, plot.bottom()))
            if width >= 48:
                y = int(plot.bottom() - 8 - (row % 3) * 13)
                row += 1
                max_chars = max(4, int(width / 6))
                txt = label if len(label) <= max_chars else label[:max_chars - 1] + "…"
                bg = QColor(255, 255, 255); bg.setAlpha(205)
                text_w = min(width - 4, max(28, 6 * len(txt) + 8))
                bx = max(plot.left() + 1, min(x1 + 3, plot.right() - text_w - 2))
                p.setPen(QPen(color, 1))
                p.setBrush(QBrush(bg))
                p.drawRoundedRect(QRectF(bx, y - 10, text_w, 12), 3, 3)
                p.drawText(int(bx + 4), y, txt)

    def _draw_event_markers(self, p: QPainter, plot: QRectF, xmin: float, xmax: float, pymin: float, pymax: float) -> None:
        if not self.show_event_markers or not self.events:
            return
        type_color = {
            STATE_DEGAS: QColor(237, 125, 49),
            STATE_TREAT: QColor(0, 150, 70),
            STATE_CLEAN_TANK: QColor(120, 70, 170),
            STATE_CLEAN_XD: QColor(0, 150, 200),
        }
        # Build time lookup by exact text.  This avoids changing EventResult dataclass.
        time_by_text: Dict[str, float] = {s.time_text: s.time_min for s in self.samples}
        p.setFont(QFont("Arial", 8))
        used_label_y = 0
        for ev in self.events:
            st = time_by_text.get(ev.start_time)
            en = time_by_text.get(ev.end_time)
            if st is None or en is None:
                continue
            x1 = self._map_x(st, plot, xmin, xmax)
            x2 = self._map_x(en, plot, xmin, xmax)
            color = type_color.get(ev.event_type, QColor(120, 120, 120))
            fill = QColor(color); fill.setAlpha(22)
            p.fillRect(QRectF(x1, plot.top(), max(1.0, x2 - x1), plot.height()), fill)
            p.setPen(QPen(color, 1, Qt.DashLine))
            p.drawLine(QPointF(x1, plot.top()), QPointF(x1, plot.bottom()))
            p.drawLine(QPointF(x2, plot.top()), QPointF(x2, plot.bottom()))
            prefix = {STATE_DEGAS: "D", STATE_TREAT: "T", STATE_CLEAN_TANK: "CT", STATE_CLEAN_XD: "CX"}.get(ev.event_type, ev.event_type[:2])
            label = f"{prefix}{ev.event_no}"
            if ev.vacuum_trend in ("UP", "DOWN", "FLAT"):
                label += f" {ev.vacuum_trend}"
            # Put labels in a reserved band above the plot so they do not cover curves.
            y = int(plot.top() - 24 + (used_label_y % 2) * 12)
            used_label_y += 1
            label_w = max(34, 7 * len(label) + 8)
            bx = max(plot.left() + 1, min(x1 + 3, plot.right() - label_w - 2))
            bg = QColor(255, 255, 255); bg.setAlpha(210)
            p.setPen(QPen(color, 1))
            p.setBrush(QBrush(bg))
            p.drawRoundedRect(QRectF(bx, y - 10, label_w, 12), 3, 3)
            p.setPen(color)
            p.drawText(int(bx + 4), y, label)

    def _draw_hover(self, p: QPainter, plot: QRectF, xmin: float, xmax: float,
                    pymin: float, pymax: float, vymin: float, vymax: float) -> None:
        if not self.show_value_popup or self._mouse_pos is None or not plot.contains(self._mouse_pos):
            return
        t = xmin + (self._mouse_pos.x() - plot.left()) / plot.width() * (xmax - xmin)
        smp = self._nearest_sample(t)
        if smp is None:
            return
        x = self._map_x(smp.time_min, plot, xmin, xmax)
        p.setPen(QPen(QColor(80, 80, 80), 1, Qt.DashLine))
        p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        lines = [f"Time: {smp.time_text}", f"State: {smp.state}"]
        if smp.do is not None: lines.append(f"DO: {smp.do:.3f} ppm")
        if smp.vacuum is not None: lines.append(f"Vacuum: {smp.vacuum:.3f}")
        if smp.second_flow is not None: lines.append(f"2nd Flow: {smp.second_flow:.3f}")
        if smp.primary_flow is not None: lines.append(f"Primary Flow: {smp.primary_flow:.3f}")
        if smp.chiller_temp is not None: lines.append(f"Chiller Temp: {smp.chiller_temp:.3f}")
        if smp.absolute_pressure is not None: lines.append(f"Absolute Pressure: {smp.absolute_pressure:.3f}")
        if smp.dynamic_pressure is not None: lines.append(f"Dynamic Pressure: {smp.dynamic_pressure:.3f}")
        box_w, line_h = 230, 17
        box_h = 10 + line_h * len(lines)
        bx = x + 12
        if bx + box_w > plot.right():
            bx = x - box_w - 12
        by = plot.top() + 8
        p.setPen(QPen(QColor(160, 160, 160), 1))
        p.setBrush(QBrush(QColor(255, 255, 245)))
        p.drawRoundedRect(QRectF(bx, by, box_w, box_h), 5, 5)
        p.setPen(QColor(40, 40, 40))
        for i, line in enumerate(lines):
            p.drawText(int(bx + 8), int(by + 18 + i * line_h), line)
        # Highlight actual points on visible series.
        if self.show_do and smp.do is not None and is_valid_do(smp.do):
            p.setBrush(QBrush(QColor(0, 80, 180)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, self._map_y(smp.do, plot, pymin, pymax)), 4, 4)
        if self.show_sf and smp.second_flow is not None and SECONDARY_FLOW_VALID_MIN <= smp.second_flow <= SECONDARY_FLOW_VALID_MAX:
            p.setBrush(QBrush(QColor(0, 140, 80)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, self._map_y(smp.second_flow, plot, pymin, pymax)), 4, 4)
        extra_points = [
            (self.show_primary_flow, smp.primary_flow, QColor(112, 48, 160)),
            (self.show_chiller_temp, smp.chiller_temp, QColor(0, 160, 160)),
            (self.show_absolute_pressure, smp.absolute_pressure, QColor(220, 150, 0)),
            (self.show_dynamic_pressure, smp.dynamic_pressure, QColor(120, 120, 120)),
        ]
        for visible, value, color in extra_points:
            if visible and value is not None:
                p.setBrush(QBrush(color)); p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(x, self._map_y(value, plot, pymin, pymax)), 4, 4)
        if self.show_vac and smp.vacuum is not None:
            p.setBrush(QBrush(QColor(180, 0, 0)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, self._map_y(smp.vacuum, plot, vymin, vymax)), 4, 4)

    def _range_value_axis(self) -> str:
        return "vacuum" if self.range_parameter == "Vacuum" else "primary"

    def _draw_range_analysis(self, p: QPainter, plot: QRectF, xmin: float, xmax: float,
                             pymin: float, pymax: float, vymin: float, vymax: float) -> None:
        if not self.range_selection:
            return
        start, end = self.range_selection
        if end < xmin or start > xmax:
            return
        left_t, right_t = max(start, xmin), min(end, xmax)
        x1 = self._map_x(left_t, plot, xmin, xmax)
        x2 = self._map_x(right_t, plot, xmin, xmax)
        fill = QColor(70, 150, 90); fill.setAlpha(42)
        p.fillRect(QRectF(x1, plot.top(), max(1.0, x2-x1), plot.height()), fill)
        p.setPen(QPen(QColor(35, 125, 65), 1, Qt.DashLine))
        p.drawRect(QRectF(x1, plot.top(), max(1.0, x2-x1), plot.height()))
        if not self.range_result:
            return
        avg = self.range_result.get("average")
        if isinstance(avg, (int, float)) and math.isfinite(avg):
            ymin, ymax = (vymin, vymax) if self._range_value_axis() == "vacuum" else (pymin, pymax)
            if ymin <= avg <= ymax:
                y = self._map_y(avg, plot, ymin, ymax)
                p.setPen(QPen(QColor(35, 125, 65), 1.3, Qt.DashDotLine))
                p.drawLine(QPointF(x1, y), QPointF(x2, y))
        if not self.show_range_overlay:
            return
        r = self.range_result
        lines = [
            f"Range Analysis — {self.range_parameter}",
            f"{self._format_minutes_as_time(start)} - {self._format_minutes_as_time(end)}",
            f"Avg {r.get('average', 0):.4g}   Min {r.get('minimum', 0):.4g}   Max {r.get('maximum', 0):.4g}",
            f"P-P {r.get('peak_to_peak', 0):.4g}   StdDev {r.get('std_dev', 0):.4g}   CV {r.get('cv_percent', 0):.3g}%",
            f"RMS noise {r.get('rms_noise', 0):.4g}   Slope {r.get('slope_per_min', 0):.4g}/min",
            f"Duration {r.get('duration_min', 0):.3f} min   Samples {r.get('sample_count', 0)}",
        ]
        box_w, line_h = 390, 16
        box_h = 10 + line_h * len(lines)
        bx = max(plot.left()+5, min(x1+6, plot.right()-box_w-5))
        by = plot.top()+26
        p.setPen(QPen(QColor(35, 125, 65), 1))
        p.setBrush(QBrush(QColor(248, 255, 248, 235)))
        p.drawRoundedRect(QRectF(bx, by, box_w, box_h), 5, 5)
        p.setPen(QColor(30, 70, 40))
        for i, line in enumerate(lines):
            p.drawText(int(bx+8), int(by+17+i*line_h), line)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        # Keep a dedicated header band for title, legend and event labels.
        margin_l, margin_r, margin_t, margin_b = 58, 58, 86, 42
        plot = QRectF(margin_l, margin_t, max(10, self.width() - margin_l - margin_r), max(10, self.height() - margin_t - margin_b))
        self._plot_rect = plot
        p.setPen(QColor(40, 40, 40))
        title = self.file_name or "No file selected"
        p.setFont(QFont("Arial", 10, QFont.Bold))
        p.drawText(8, 18, title)
        p.setFont(QFont("Arial", 8))
        p.drawText(8, 34, "Hover to inspect Time / State / DO / Vacuum / Flow / Pressure / Temperature")
        if not self.samples:
            p.setPen(QColor(100, 100, 100)); p.drawText(self.rect(), Qt.AlignCenter, "No chart data")
            return
        xmin, xmax = self._time_range()
        pymin, pymax = self._primary_range()
        vymin, vymax = self._vacuum_range()
        self._draw_axes(p, plot, xmin, xmax, pymin, pymax, vymin, vymax)
        self._draw_non_event_labels(p, plot, xmin, xmax)
        self._draw_event_markers(p, plot, xmin, xmax, pymin, pymax)
        visible_samples = [s for s in self.samples if xmin <= s.time_min <= xmax]
        do_vals = [(s.time_min, s.do) for s in visible_samples if s.do is not None and is_valid_do(s.do)]
        vac_vals = [(s.time_min, s.vacuum) for s in visible_samples if s.vacuum is not None]
        sf_vals = [(s.time_min, s.second_flow) for s in visible_samples if s.second_flow is not None and SECONDARY_FLOW_VALID_MIN <= s.second_flow <= SECONDARY_FLOW_VALID_MAX]
        pf_vals = [(s.time_min, s.primary_flow) for s in visible_samples if s.primary_flow is not None]
        ct_vals = [(s.time_min, s.chiller_temp) for s in visible_samples if s.chiller_temp is not None]
        ap_vals = [(s.time_min, s.absolute_pressure) for s in visible_samples if s.absolute_pressure is not None]
        dp_vals = [(s.time_min, s.dynamic_pressure) for s in visible_samples if s.dynamic_pressure is not None]
        if self.show_do:
            self._draw_line_series(p, plot, do_vals, xmin, xmax, pymin, pymax, QColor(0, 80, 180), 1.6)
        if self.show_sf:
            self._draw_line_series(p, plot, sf_vals, xmin, xmax, pymin, pymax, QColor(0, 140, 80), 1.3)
        if self.show_primary_flow:
            self._draw_line_series(p, plot, pf_vals, xmin, xmax, pymin, pymax, QColor(112, 48, 160), 1.2)
        if self.show_chiller_temp:
            self._draw_line_series(p, plot, ct_vals, xmin, xmax, pymin, pymax, QColor(0, 160, 160), 1.2)
        if self.show_absolute_pressure:
            self._draw_line_series(p, plot, ap_vals, xmin, xmax, pymin, pymax, QColor(220, 150, 0), 1.2)
        if self.show_dynamic_pressure:
            self._draw_line_series(p, plot, dp_vals, xmin, xmax, pymin, pymax, QColor(120, 120, 120), 1.2)
        if self.show_vac:
            self._draw_line_series(p, plot, vac_vals, xmin, xmax, vymin, vymax, QColor(180, 0, 0), 1.4)
        # Legend. Wrap across rows to keep all active sensors visible.
        legend = [
            ("DO", QColor(0, 80, 180), self.show_do),
            ("Vacuum", QColor(180, 0, 0), self.show_vac),
            ("2nd Flow", QColor(0, 140, 80), self.show_sf),
            ("Primary Flow", QColor(112, 48, 160), self.show_primary_flow),
            ("Chiller Temp", QColor(0, 160, 160), self.show_chiller_temp),
            ("Abs Pressure", QColor(220, 150, 0), self.show_absolute_pressure),
            ("Dyn Pressure", QColor(120, 120, 120), self.show_dynamic_pressure),
        ]
        lx = int(plot.left()); ly = 54
        for name, color, visible in legend:
            if not visible: continue
            if lx > plot.right() - 120:
                lx = int(plot.left()); ly += 16
            p.setPen(QPen(color, 2)); p.drawLine(lx, ly, lx + 22, ly)
            p.setPen(QColor(50, 50, 50)); p.drawText(lx + 28, ly + 4, name)
            lx += 110

        # Draw drag-to-zoom selection overlay after curves/legend so the target range is visible.
        if self._is_dragging and self._drag_start is not None and self._drag_current is not None:
            x1 = max(plot.left(), min(self._drag_start.x(), plot.right()))
            x2 = max(plot.left(), min(self._drag_current.x(), plot.right()))
            left = min(x1, x2); width = abs(x2 - x1)
            if width >= 1:
                fill = QColor(80, 130, 220); fill.setAlpha(45)
                p.fillRect(QRectF(left, plot.top(), width, plot.height()), fill)
                p.setPen(QPen(QColor(40, 90, 180), 1, Qt.DashLine))
                p.drawRect(QRectF(left, plot.top(), width, plot.height()))
                t1 = self._plot_x_to_time(left)
                t2 = self._plot_x_to_time(left + width)
                if t1 is not None and t2 is not None:
                    mode_name = "Analyze" if self.range_analysis_enabled else "Zoom"
                    txt = f"{mode_name}: {self._format_minutes_as_time(t1)} - {self._format_minutes_as_time(t2)}"
                    p.setPen(QColor(40, 40, 40))
                    p.setBrush(QBrush(QColor(255, 255, 255, 230)))
                    p.drawRoundedRect(QRectF(left + 4, plot.top() + 4, 220, 18), 3, 3)
                    p.drawText(int(left + 10), int(plot.top() + 18), txt)
        self._draw_range_analysis(p, plot, xmin, xmax, pymin, pymax, vymin, vymax)
        self._draw_hover(p, plot, xmin, xmax, pymin, pymax, vymin, vymax)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.resize(1200, 780)
        self.files: List[str] = []
        self.results: List[EventResult] = []
        self.summaries: List[FileSummary] = []
        self.current_samples: List[Sample] = []
        self.current_range_result: Optional[Dict[str, Any]] = None
        self.sample_cache: Dict[str, List[Sample]] = {}
        self.worker: Optional[AnalyzeWorker] = None
        self._temp_roots: List[str] = []
        self.setAcceptDrops(True)
        self._build_ui()
        self._setup_guide_system()


    def _setup_guide_system(self) -> None:
        pages = [
            GuidePage(
                "1. Import files and automatic analysis",
                "<p>Drop a WaterSystem log, folder, or ZIP archive onto the application, "
                "or use <b>Select Files / ZIP</b> and <b>Select Folder</b>.</p>"
                "<p>The application finds matching WaterSystem files inside folders and ZIP archives "
                "and starts analysis automatically. There is no separate Analyze button.</p>",
            ),
            GuidePage(
                "2. Import / Settings panel",
                "<p>Use <b>Show Import / Settings</b> to expand the upper control area. "
                "Collapse it again to maximize the chart.</p>"
                "<p>The judgment settings control minimum DO change, high/low DO averaging band, "
                "and Vacuum FLAT tolerance.</p>",
            ),
            GuidePage(
                "3. Review analysis results",
                "<p><b>Event Results</b> shows each detected event. "
                "<b>File Summary</b> shows totals for every loaded file.</p>"
                "<p>Select a result row to move directly to the corresponding file and event in the Chart tab.</p>",
            ),
            GuidePage(
                "4. Chart display controls",
                "<p>Use the checkboxes above the chart to show or hide DO, Vacuum, flow, pressure, "
                "temperature, and event labels.</p>"
                "<p><b>Non-event labels</b> shows actual Treatment Pause and Degas Pause states, plus labels outside detected Treat/Clean events. "
                "<b>Value popup</b> turns the mouse-over value display on or off.</p>",
            ),
            GuidePage(
                "5. Zoom and navigation",
                "<p>Use the collapsible <b>Range Analysis</b> panel to select a sensor and measure variation in a mouse-drawn interval. When disabled, horizontal dragging zooms the X-axis. "
                "You can also enter start and end times and press <b>Apply Zoom</b>.</p>"
                "<p>Use <b>Reset Zoom</b> to return to the complete time range. "
                "The left and right arrow buttons switch the displayed file.</p>",
            ),
            GuidePage(
                "6. Export and projects",
                "<p><b>Export CSV</b> saves analysis results. <b>Save Project</b> stores the current file list, "
                "settings, and chart options. <b>Load Project</b> restores them.</p>"
                "<p>ZIP extraction is temporary and is cleaned up when the application closes.</p>",
            ),
            GuidePage(
                "7. Guide settings",
                "<p>At startup, choose <b>Yes — Show Guide</b> to open this guide, or "
                "<b>No — Do Not Ask Again</b> to disable the startup question.</p>"
                "<p>The Help menu can open the guide at any time or restore the startup question. "
                "When closing the app, select <b>Show the guide and guided tour at the next startup</b> "
                "to display it once on the next launch.</p>",
            ),
        ]
        if RELEASE_MODE:
            self.guide_manager = None
            return

        self.guide_manager = GuideManager(
            self,
            GuideConfig(
                app_name=APP_NAME,
                settings_vendor="InSightec",
                settings_product="DO_Analysis_Qt",
                guide_title=f"{APP_NAME} — Quick Guide and Guided Tour",
            ),
            pages,
        )

        help_menu = self.menuBar().addMenu("Help")
        action_guide = QAction("Quick Guide and Guided Tour", self)
        action_guide.triggered.connect(self.guide_manager.show_guide)
        help_menu.addAction(action_guide)
        action_reset = QAction("Show startup guide question again", self)
        action_reset.triggered.connect(self._reset_guide_prompt)
        help_menu.addAction(action_reset)
        self.guide_manager.schedule_startup_check()

    def _reset_guide_prompt(self) -> None:
        if RELEASE_MODE or self.guide_manager is None:
            return
        self.guide_manager.reset_startup_prompt()
        QMessageBox.information(
            self,
            APP_NAME,
            "The Quick Guide question will be shown at the next startup.",
        )

    def _cleanup_before_close(self) -> None:
        for root in self._temp_roots:
            shutil.rmtree(root, ignore_errors=True)
        self._temp_roots.clear()

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(6, 6, 6, 6)
        main.setSpacing(4)

        # Compact header remains visible while the import/settings area is folded.
        compact = QHBoxLayout()
        self.btn_toggle_controls = QPushButton("▼ Hide Import / Settings")
        self.btn_toggle_controls.setCheckable(True)
        self.btn_toggle_controls.setChecked(True)
        compact.addWidget(self.btn_toggle_controls)
        self.compact_file_status = QLabel("No files loaded")
        compact.addWidget(self.compact_file_status, 1)
        main.addLayout(compact)

        self.control_panel = QWidget()
        panel_layout = QVBoxLayout(self.control_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(4)

        top = QHBoxLayout()
        self.btn_files = QPushButton("Select Files / ZIP")
        self.btn_folder = QPushButton("Select Folder")
        self.btn_export = QPushButton("Export CSV")
        self.btn_save = QPushButton("Save Project")
        self.btn_load = QPushButton("Load Project")
        for b in [self.btn_files,self.btn_folder,self.btn_export,self.btn_save,self.btn_load]:
            top.addWidget(b)
        panel_layout.addLayout(top)

        self.drop_hint = QLabel("Drop WaterSystem files, folders, or ZIP archives here")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setMinimumHeight(42)
        self.drop_hint.setStyleSheet("QLabel { border: 2px dashed #8a9aaa; border-radius: 8px; background: #f5f8fb; color: #405060; font-weight: 600; padding: 6px; }")
        panel_layout.addWidget(self.drop_hint)

        opts = QGroupBox("Judgment settings")
        grid = QGridLayout(opts)
        self.sp_min_do = QDoubleSpinBox(); self.sp_min_do.setRange(0.0, 5.0); self.sp_min_do.setDecimals(2); self.sp_min_do.setValue(MIN_DO_CHANGE_FOR_VACUUM); self.sp_min_do.setSuffix(" ppm")
        self.sp_band = QDoubleSpinBox(); self.sp_band.setRange(0.01, 1.0); self.sp_band.setDecimals(2); self.sp_band.setValue(DO_AVG_BAND); self.sp_band.setSuffix(" ppm")
        self.sp_flat = QDoubleSpinBox(); self.sp_flat.setRange(0.0, 5.0); self.sp_flat.setDecimals(2); self.sp_flat.setValue(VACUUM_FLAT_TOLERANCE)
        grid.addWidget(QLabel("Min DO change for Vacuum judgment"),0,0); grid.addWidget(self.sp_min_do,0,1)
        grid.addWidget(QLabel("High/Low DO average band"),0,2); grid.addWidget(self.sp_band,0,3)
        grid.addWidget(QLabel("Vacuum FLAT tolerance"),0,4); grid.addWidget(self.sp_flat,0,5)
        panel_layout.addWidget(opts)

        self.progress = QProgressBar(); panel_layout.addWidget(self.progress)
        self.status = QLabel("Ready"); panel_layout.addWidget(self.status)
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(80); panel_layout.addWidget(self.log)
        main.addWidget(self.control_panel)

        self.tabs = QTabWidget(); main.addWidget(self.tabs, 1)

        result_page = QWidget(); res_layout = QVBoxLayout(result_page)
        self.result_table = QTableWidget(0, 15)
        self.result_table.setHorizontalHeaderLabels(["File","Type","No","Start","End","Duration","Max DO","Min DO","DO Change","High DO Vac","Low DO Vac","Diff","Trend","2nd Flow Avg","Note"])
        res_layout.addWidget(self.result_table)
        self.tabs.addTab(result_page, "Event Results")

        summary_page = QWidget(); sum_layout = QVBoxLayout(summary_page)
        self.summary_table = QTableWidget(0, 8)
        self.summary_table.setHorizontalHeaderLabels(["File","Samples","Events","UP","FLAT","DOWN","N/A","Path"])
        sum_layout.addWidget(self.summary_table)
        self.tabs.addTab(summary_page, "File Summary")

        chart_page = QWidget(); chart_layout = QVBoxLayout(chart_page)
        chart_layout.setContentsMargins(4, 4, 4, 4)
        chart_layout.setSpacing(3)
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Displayed file"))
        self.btn_prev_chart_file = QPushButton("◀")
        self.btn_prev_chart_file.setFixedWidth(34)
        file_row.addWidget(self.btn_prev_chart_file)
        self.chart_file_combo = QComboBox()
        self.chart_file_combo.setMinimumWidth(360)
        file_row.addWidget(self.chart_file_combo, 1)
        self.btn_next_chart_file = QPushButton("▶")
        self.btn_next_chart_file.setFixedWidth(34)
        file_row.addWidget(self.btn_next_chart_file)
        self.btn_reload_chart_file = QPushButton("Reload")
        file_row.addWidget(self.btn_reload_chart_file)
        chart_layout.addLayout(file_row)
        cbrow = QHBoxLayout()
        self.cb_all = QCheckBox("ALL"); self.cb_all.setChecked(False)
        self.cb_do = QCheckBox("DO"); self.cb_do.setChecked(True)
        self.cb_vac = QCheckBox("Vacuum"); self.cb_vac.setChecked(True)
        self.cb_sf = QCheckBox("2nd Flow"); self.cb_sf.setChecked(True)
        self.cb_pf = QCheckBox("Primary Flow"); self.cb_pf.setChecked(False)
        self.cb_chiller = QCheckBox("Chiller Temp"); self.cb_chiller.setChecked(False)
        self.cb_abs = QCheckBox("AbsolutePressure"); self.cb_abs.setChecked(False)
        self.cb_dyn = QCheckBox("DynamicPressure"); self.cb_dyn.setChecked(False)
        self.cb_events = QCheckBox("Treat/Clean event labels"); self.cb_events.setChecked(True)
        self.cb_non_events = QCheckBox("Non-event labels"); self.cb_non_events.setChecked(False)
        self.cb_value_popup = QCheckBox("Value popup"); self.cb_value_popup.setChecked(True)
        self.cb_value_popup.setToolTip("Show or hide the chart value popup while moving the mouse over the chart.")
        for c in [self.cb_all,self.cb_do,self.cb_vac,self.cb_sf,self.cb_pf,self.cb_chiller,self.cb_abs,self.cb_dyn,self.cb_events,self.cb_non_events,self.cb_value_popup]: cbrow.addWidget(c)
        cbrow.addStretch(); chart_layout.addLayout(cbrow)
        note = QLabel("Checked items update immediately. Drag across the chart to zoom the X-axis.")
        chart_layout.addWidget(note)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("X zoom start"))
        self.zoom_start = QLineEdit(); self.zoom_start.setPlaceholderText("HH:MM:SS.000")
        zoom_row.addWidget(self.zoom_start)
        zoom_row.addWidget(QLabel("X zoom end"))
        self.zoom_end = QLineEdit(); self.zoom_end.setPlaceholderText("HH:MM:SS.000")
        zoom_row.addWidget(self.zoom_end)
        self.btn_apply_zoom = QPushButton("Apply Zoom")
        self.btn_reset_zoom = QPushButton("Reset Zoom")
        zoom_row.addWidget(self.btn_apply_zoom)
        zoom_row.addWidget(self.btn_reset_zoom)
        chart_layout.addLayout(zoom_row)

        self.btn_toggle_range = QPushButton("▶ Range Analysis")
        self.btn_toggle_range.setCheckable(True)
        self.btn_toggle_range.setChecked(False)
        chart_layout.addWidget(self.btn_toggle_range)
        self.range_panel = QWidget()
        range_grid = QGridLayout(self.range_panel)
        range_grid.setContentsMargins(8, 2, 8, 4)
        self.cb_range_enable = QCheckBox("Enable Range Analysis")
        self.cb_range_overlay = QCheckBox("Show result on chart")
        self.cb_range_overlay.setChecked(True)
        self.range_parameter_combo = QComboBox()
        self.range_parameter_combo.addItems(["DO Level", "Vacuum", "2nd Flow", "Primary Flow", "Chiller Temperature", "Absolute Pressure", "Dynamic Pressure"])
        self.range_result_label = QLabel("Enable Range Analysis, then drag horizontally across the chart.")
        self.range_result_label.setWordWrap(True)
        self.btn_range_copy = QPushButton("Copy Result")
        self.btn_range_export = QPushButton("Export Range CSV")
        self.btn_range_clear = QPushButton("Clear Range")
        range_grid.addWidget(self.cb_range_enable, 0, 0)
        range_grid.addWidget(QLabel("Parameter"), 0, 1)
        range_grid.addWidget(self.range_parameter_combo, 0, 2)
        range_grid.addWidget(self.cb_range_overlay, 0, 3)
        range_grid.addWidget(self.btn_range_copy, 0, 4)
        range_grid.addWidget(self.btn_range_export, 0, 5)
        range_grid.addWidget(self.btn_range_clear, 0, 6)
        range_grid.addWidget(self.range_result_label, 1, 0, 1, 7)
        self.range_panel.setVisible(False)
        chart_layout.addWidget(self.range_panel)

        chart_split = QSplitter(Qt.Vertical)
        self.chart = ChartWidget(); self.chart.zoomSelected.connect(self.on_chart_drag_zoom_selected); self.chart.rangeSelected.connect(self.on_chart_range_selected); chart_split.addWidget(self.chart)
        event_box = QWidget(); event_layout = QVBoxLayout(event_box); event_layout.setContentsMargins(0, 0, 0, 0)
        event_layout.addWidget(QLabel("Event Results for displayed file"))
        self.chart_event_table = QTableWidget(0, 11)
        self.chart_event_table.setHorizontalHeaderLabels(["Type","No","Start","End","Duration","Max DO","Min DO","DO Change","Trend","Diff","Note"])
        event_layout.addWidget(self.chart_event_table)
        chart_split.addWidget(event_box)
        chart_split.setSizes([560, 120])
        chart_split.setStretchFactor(0, 5)
        chart_split.setStretchFactor(1, 1)
        chart_layout.addWidget(chart_split, 1)
        self.tabs.addTab(chart_page, "Chart")

        # HP / Replacement and Forecast tabs were removed from the visible UI.
        self.hp_text = QTextEdit(); self.hp_text.hide()
        self.repl_text = QTextEdit(); self.repl_text.hide()
        self.forecast_btn = QPushButton("Create Simple Forecast"); self.forecast_btn.hide()
        self.forecast_text = QTextEdit(); self.forecast_text.hide(); self.forecast_text.setReadOnly(True)

        self.btn_toggle_controls.toggled.connect(self.set_control_panel_expanded)
        self.btn_files.clicked.connect(self.select_files)
        self.btn_folder.clicked.connect(self.select_folder)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_save.clicked.connect(self.save_project)
        self.btn_load.clicked.connect(self.load_project)
        self.forecast_btn.clicked.connect(self.create_forecast)
        self.cb_all.stateChanged.connect(self.set_all_chart_items)
        for cb in [self.cb_do,self.cb_vac,self.cb_sf,self.cb_pf,self.cb_chiller,self.cb_abs,self.cb_dyn,self.cb_events,self.cb_non_events,self.cb_value_popup]: cb.stateChanged.connect(self.refresh_chart_options)
        self.chart_file_combo.currentIndexChanged.connect(self.on_chart_file_changed)
        self.btn_prev_chart_file.clicked.connect(lambda: self.step_chart_file(-1))
        self.btn_next_chart_file.clicked.connect(lambda: self.step_chart_file(1))
        self.btn_reload_chart_file.clicked.connect(self.reload_current_chart_file)
        self.btn_apply_zoom.clicked.connect(self.apply_x_zoom)
        self.btn_reset_zoom.clicked.connect(self.reset_x_zoom)
        self.btn_toggle_range.toggled.connect(self.set_range_panel_expanded)
        self.cb_range_enable.toggled.connect(self.refresh_range_mode)
        self.cb_range_overlay.toggled.connect(self.refresh_range_mode)
        self.range_parameter_combo.currentTextChanged.connect(self.on_range_parameter_changed)
        self.btn_range_clear.clicked.connect(self.clear_range_analysis)
        self.btn_range_copy.clicked.connect(self.copy_range_result)
        self.btn_range_export.clicked.connect(self.export_range_csv)
        self.result_table.itemSelectionChanged.connect(self.on_result_selected)

        # Start compact so the chart receives the largest possible area.
        self.btn_toggle_controls.setChecked(False)
        self.set_control_panel_expanded(False)

    def set_control_panel_expanded(self, expanded: bool) -> None:
        self.control_panel.setVisible(expanded)
        self.btn_toggle_controls.setText("▼ Hide Import / Settings" if expanded else "▶ Show Import / Settings")

    def step_chart_file(self, delta: int) -> None:
        count = self.chart_file_combo.count()
        if count <= 0:
            return
        self.chart_file_combo.setCurrentIndex((self.chart_file_combo.currentIndex() + delta) % count)

    def log_msg(self, msg: str) -> None:
        self.log.append(msg)
        self.status.setText(msg)
        if hasattr(self, "compact_file_status"):
            count = len(self.files)
            self.compact_file_status.setText(f"{count} file(s) loaded — {msg}" if count else msg)

    @staticmethod
    def _looks_like_watersystem_file(path: Path) -> bool:
        if not path.is_file() or path.suffix.lower() not in {".txt", ".log", ".csv"}:
            return False
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for _ in range(250):
                    line = fh.readline()
                    if not line:
                        break
                    if HEADER_RE.search(line):
                        normalized = normalize_header(line)
                        return "mainstate" in normalized and "vacuumlevel" in normalized and "dolevel" in normalized
        except (OSError, UnicodeError):
            return False
        return False

    def _discover_watersystem_files(self, root: Path) -> List[str]:
        candidates = [root] if root.is_file() else list(root.rglob("*"))
        found = [str(p.resolve()) for p in candidates if self._looks_like_watersystem_file(p)]
        return sorted(set(found), key=lambda x: os.path.getmtime(x), reverse=True)

    def _extract_zip(self, zip_path: Path) -> List[str]:
        temp_root = Path(tempfile.mkdtemp(prefix="DO_Analysis_ZIP_"))
        self._temp_roots.append(str(temp_root))
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                base = temp_root.resolve()
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    target = (temp_root / info.filename).resolve()
                    if base not in target.parents:
                        raise ValueError(f"Unsafe ZIP entry was blocked: {info.filename}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info, "r") as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
            return self._discover_watersystem_files(temp_root)
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            if str(temp_root) in self._temp_roots:
                self._temp_roots.remove(str(temp_root))
            raise

    def import_paths(self, paths: List[str]) -> None:
        discovered: List[str] = []
        messages: List[str] = []
        for raw in paths:
            path = Path(raw)
            try:
                if path.is_file() and path.suffix.lower() == ".zip":
                    items = self._extract_zip(path)
                    discovered.extend(items)
                    messages.append(f"ZIP: {path.name} -> {len(items)} matching file(s)")
                elif path.is_dir():
                    items = self._discover_watersystem_files(path)
                    discovered.extend(items)
                    messages.append(f"Folder: {path.name} -> {len(items)} matching file(s)")
                elif self._looks_like_watersystem_file(path):
                    discovered.append(str(path.resolve()))
                else:
                    messages.append(f"Skipped unsupported file: {path.name}")
            except (OSError, zipfile.BadZipFile, ValueError) as exc:
                messages.append(f"Failed: {path.name}: {exc}")

        unique = list(dict.fromkeys(discovered))
        if not unique:
            QMessageBox.warning(self, APP_NAME, "No matching WaterSystem log files were found.")
            for msg in messages:
                self.log_msg(msg)
            return
        self.files = unique
        self.results = []
        self.summaries = []
        self.sample_cache.clear()
        self.populate_chart_file_combo()
        self.load_chart_file(self.files[0])
        for msg in messages:
            self.log_msg(msg)
        self.log_msg(f"Ready: {len(self.files)} WaterSystem file(s). Starting analysis automatically...")
        self.status.setText("Starting analysis...")
        QTimer.singleShot(0, self.analyze)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            self.drop_hint.setStyleSheet("QLabel { border: 2px solid #4b8bd8; border-radius: 8px; background: #eaf3ff; color: #204f80; font-weight: 700; padding: 8px; }")
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.drop_hint.setStyleSheet("QLabel { border: 2px dashed #8a9aaa; border-radius: 8px; background: #f5f8fb; color: #405060; font-weight: 600; padding: 8px; }")
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self.drop_hint.setStyleSheet("QLabel { border: 2px dashed #8a9aaa; border-radius: 8px; background: #f5f8fb; color: #405060; font-weight: 600; padding: 8px; }")
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.import_paths(paths)
        else:
            event.ignore()

    def closeEvent(self, event) -> None:
        if not RELEASE_MODE and getattr(self, "guide_manager", None) is not None:
            self.guide_manager.handle_close_event(event, self._cleanup_before_close)
        else:
            self._cleanup_before_close()
            event.accept()

    def select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select WaterSystem logs or ZIP archives", "", "Supported files (*.txt *.log *.csv *.zip);;ZIP archives (*.zip);;Log files (*.txt *.log *.csv);;All files (*.*)")
        if files:
            self.import_paths(files)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.import_paths([folder])

    def analyze(self) -> None:
        if not self.files:
            return
        if self.worker is not None and self.worker.isRunning():
            return
        self.btn_files.setEnabled(False)
        self.btn_folder.setEnabled(False)
        self.progress.setValue(0)
        self.worker = AnalyzeWorker(self.files, self.sp_min_do.value(), self.sp_band.value(), self.sp_flat.value())
        self.worker.progress.connect(lambda p, m: (self.progress.setValue(p), self.status.setText(m)))
        self.worker.finished.connect(self.analysis_finished)
        self.worker.failed.connect(self.analysis_failed)
        self.worker.start()

    def analysis_finished(self, results: list, summaries: list, errors: str) -> None:
        self.results = results
        self.summaries = summaries
        self.populate_tables()
        self.btn_files.setEnabled(True)
        self.btn_folder.setEnabled(True)
        self.worker = None
        if self.files:
            try:
                samples, _ = WaterSystemParser().parse_file(self.files[0])
                self.current_samples = samples
                fname = Path(self.files[0]).name
                self.chart.set_samples(samples, fname, self.events_for_file(fname))
            except Exception:
                pass
        self.log_msg(f"Completed. Events: {len(results)} Files: {len(summaries)}")
        self.tabs.setCurrentIndex(2)
        self.btn_toggle_controls.setChecked(False)
        if errors:
            self.log_msg("Errors:\n" + errors)

    def analysis_failed(self, msg: str) -> None:
        self.btn_files.setEnabled(True)
        self.btn_folder.setEnabled(True)
        self.worker = None
        QMessageBox.critical(self, APP_NAME, msg)

    def fmt(self, v: Optional[float], nd: int = 2) -> str:
        return "" if v is None else f"{v:.{nd}f}"

    def populate_tables(self) -> None:
        self.result_table.setRowCount(len(self.results))
        for r, item in enumerate(self.results):
            vals = [item.file_name,item.event_type,str(item.event_no),item.start_time,item.end_time,self.fmt(item.duration_min,1),self.fmt(item.max_do),self.fmt(item.min_do),self.fmt(item.do_change),self.fmt(item.high_do_vac),self.fmt(item.low_do_vac),self.fmt(item.vac_diff),item.vacuum_trend,self.fmt(item.second_flow_avg),item.note]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                if c == 12:
                    if v == "UP": cell.setBackground(QColor(220, 255, 220))
                    elif v == "DOWN": cell.setBackground(QColor(255, 220, 220))
                    elif v == "FLAT": cell.setBackground(QColor(245, 245, 210))
                self.result_table.setItem(r, c, cell)
        self.result_table.resizeColumnsToContents()
        self.summary_table.setRowCount(len(self.summaries))
        for r, s in enumerate(self.summaries):
            vals = [s.file_name,str(s.sample_count),str(s.event_count),str(s.up_count),str(s.flat_count),str(s.down_count),str(s.na_count),s.file_path]
            for c, v in enumerate(vals): self.summary_table.setItem(r,c,QTableWidgetItem(v))
        self.summary_table.resizeColumnsToContents()

    def populate_chart_file_combo(self) -> None:
        self.chart_file_combo.blockSignals(True)
        self.chart_file_combo.clear()
        for f in self.files:
            self.chart_file_combo.addItem(Path(f).name, f)
        self.chart_file_combo.blockSignals(False)
        self.compact_file_status.setText(f"{len(self.files)} file(s) loaded" if self.files else "No files loaded")

    def events_for_file(self, file_name: str) -> List[EventResult]:
        return [r for r in self.results if r.file_name == file_name]

    def _time_text_to_visible_minutes(self, text: str) -> Optional[float]:
        base = parse_time_minutes(text.strip().replace(".", ":"))
        if base is None:
            # Accept HH:MM:SS.mmm as well.
            m = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?$", text.strip())
            if not m:
                return None
            h, mi, sec, ms = m.groups()
            base = int(h) * 60.0 + int(mi) + int(sec) / 60.0 + int(ms or 0) / 60000.0
        if not self.current_samples:
            return base
        data_min = min(s.time_min for s in self.current_samples)
        data_max = max(s.time_min for s in self.current_samples)
        candidates = [base + 1440.0 * k for k in range(-2, 4)]
        inside = [c for c in candidates if data_min - 0.01 <= c <= data_max + 0.01]
        if inside:
            return min(inside, key=lambda c: abs(c - data_min))
        return min(candidates, key=lambda c: min(abs(c - data_min), abs(c - data_max)))

    def populate_chart_event_table(self, file_name: str) -> None:
        events = self.events_for_file(file_name)
        self.chart_event_table.setRowCount(len(events))
        for r, item in enumerate(events):
            vals = [item.event_type, str(item.event_no), item.start_time, item.end_time,
                    self.fmt(item.duration_min, 1), self.fmt(item.max_do), self.fmt(item.min_do),
                    self.fmt(item.do_change), item.vacuum_trend, self.fmt(item.vac_diff), item.note]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                if c == 8:
                    if v == "UP": cell.setBackground(QColor(220, 255, 220))
                    elif v == "DOWN": cell.setBackground(QColor(255, 220, 220))
                    elif v == "FLAT": cell.setBackground(QColor(245, 245, 210))
                self.chart_event_table.setItem(r, c, cell)
        self.chart_event_table.resizeColumnsToContents()

    def update_zoom_text_from_samples(self) -> None:
        if not self.current_samples:
            self.zoom_start.clear(); self.zoom_end.clear(); return
        self.zoom_start.setText(self.chart._format_minutes_as_time(min(s.time_min for s in self.current_samples)))
        self.zoom_end.setText(self.chart._format_minutes_as_time(max(s.time_min for s in self.current_samples)))


    def set_range_panel_expanded(self, expanded: bool) -> None:
        self.range_panel.setVisible(expanded)
        self.btn_toggle_range.setText("▼ Range Analysis" if expanded else "▶ Range Analysis")

    def refresh_range_mode(self) -> None:
        self.chart.set_range_analysis(
            self.cb_range_enable.isChecked(),
            self.range_parameter_combo.currentText(),
            self.cb_range_overlay.isChecked(),
        )
        mode = "range analysis" if self.cb_range_enable.isChecked() else "zoom"
        self.status.setText(f"Chart drag mode: {mode}")

    def on_range_parameter_changed(self, _text: str) -> None:
        self.clear_range_analysis()
        self.refresh_range_mode()

    @staticmethod
    def _range_parameter_value(sample: Sample, parameter: str) -> Optional[float]:
        mapping = {
            "DO Level": sample.do,
            "Vacuum": sample.vacuum,
            "2nd Flow": sample.second_flow,
            "Primary Flow": sample.primary_flow,
            "Chiller Temperature": sample.chiller_temp,
            "Absolute Pressure": sample.absolute_pressure,
            "Dynamic Pressure": sample.dynamic_pressure,
        }
        value = mapping.get(parameter)
        if value is None or not math.isfinite(value):
            return None
        if parameter == "DO Level" and not is_valid_do(value):
            return None
        if parameter == "2nd Flow" and not (SECONDARY_FLOW_VALID_MIN <= value <= SECONDARY_FLOW_VALID_MAX):
            return None
        return value

    def on_chart_range_selected(self, start: float, end: float) -> None:
        parameter = self.range_parameter_combo.currentText()
        points = [(s.time_min, self._range_parameter_value(s, parameter)) for s in self.current_samples if start <= s.time_min <= end]
        clean = [(t, v) for t, v in points if v is not None]
        if len(clean) < 2:
            self.current_range_result = None
            self.chart.clear_range_analysis()
            self.range_result_label.setText(f"No sufficient valid {parameter} samples in the selected range.")
            self.status.setText("Range analysis: insufficient samples")
            return
        times = [t for t, _ in clean]
        values = [float(v) for _, v in clean]
        avg = statistics.fmean(values)
        minimum, maximum = min(values), max(values)
        std_dev = statistics.pstdev(values) if len(values) > 1 else 0.0
        rms_noise = math.sqrt(statistics.fmean([(v-avg)**2 for v in values]))
        cv = abs(std_dev / avg * 100.0) if abs(avg) > 1e-12 else 0.0
        xavg = statistics.fmean(times)
        denom = sum((t-xavg)**2 for t in times)
        slope = sum((t-xavg)*(v-avg) for t, v in clean) / denom if denom > 0 else 0.0
        result = {
            "file": Path(str(self.chart_file_combo.currentData() or "")).name,
            "parameter": parameter,
            "start_min": start, "end_min": end,
            "start_time": self.chart._format_minutes_as_time(start),
            "end_time": self.chart._format_minutes_as_time(end),
            "duration_min": end-start, "sample_count": len(values),
            "average": avg, "minimum": minimum, "maximum": maximum,
            "peak_to_peak": maximum-minimum, "std_dev": std_dev,
            "cv_percent": cv, "rms_noise": rms_noise, "slope_per_min": slope,
        }
        self.current_range_result = result
        self.chart.set_range_result(start, end, result)
        self.range_result_label.setText(
            f"{parameter} | {result['start_time']} - {result['end_time']} | "
            f"Avg {avg:.6g}, Min {minimum:.6g}, Max {maximum:.6g}, P-P {maximum-minimum:.6g}, "
            f"StdDev {std_dev:.6g}, CV {cv:.4g}%, RMS noise {rms_noise:.6g}, "
            f"Slope {slope:.6g}/min, Duration {end-start:.3f} min, Samples {len(values)}"
        )
        self.status.setText(f"Range analyzed: {parameter}, {len(values)} samples")

    def clear_range_analysis(self) -> None:
        self.current_range_result = None
        self.chart.clear_range_analysis()
        self.range_result_label.setText("Enable Range Analysis, then drag horizontally across the chart.")

    def _range_result_rows(self) -> List[Tuple[str, Any]]:
        if not self.current_range_result:
            return []
        order = ["file", "parameter", "start_time", "end_time", "duration_min", "sample_count", "average", "minimum", "maximum", "peak_to_peak", "std_dev", "cv_percent", "rms_noise", "slope_per_min"]
        return [(key, self.current_range_result.get(key, "")) for key in order]

    def copy_range_result(self) -> None:
        rows = self._range_result_rows()
        if not rows:
            QMessageBox.information(self, APP_NAME, "Select and analyze a range first.")
            return
        QApplication.clipboard().setText("\n".join(f"{k}: {v}" for k, v in rows))
        self.status.setText("Range analysis result copied")

    def export_range_csv(self) -> None:
        rows = self._range_result_rows()
        if not rows:
            QMessageBox.information(self, APP_NAME, "Select and analyze a range first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Range Analysis", "RangeAnalysis.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow([k for k, _ in rows])
            writer.writerow([v for _, v in rows])
        self.status.setText(f"Range CSV exported: {Path(path).name}")

    def on_chart_drag_zoom_selected(self, start: float, end: float) -> None:
        self.zoom_start.setText(self.chart._format_minutes_as_time(start))
        self.zoom_end.setText(self.chart._format_minutes_as_time(end))
        self.status.setText(f"Drag zoom: {self.chart._format_minutes_as_time(start)} - {self.chart._format_minutes_as_time(end)}")

    def apply_x_zoom(self) -> None:
        start = self._time_text_to_visible_minutes(self.zoom_start.text())
        end = self._time_text_to_visible_minutes(self.zoom_end.text())
        if start is None or end is None:
            QMessageBox.warning(self, APP_NAME, "Use time format like HH:MM:SS.000 for zoom start/end.")
            return
        if end <= start:
            end += 1440.0
        self.chart.set_zoom_range(start, end)
        self.status.setText(f"Zoom: {self.chart._format_minutes_as_time(start)} - {self.chart._format_minutes_as_time(end)}")

    def reset_x_zoom(self) -> None:
        self.chart.reset_zoom()
        self.update_zoom_text_from_samples()
        self.status.setText("Zoom reset")

    def load_chart_file(self, file_path: str, force_reload: bool = False) -> None:
        if not file_path:
            return
        try:
            if force_reload or file_path not in self.sample_cache:
                samples, _ = WaterSystemParser().parse_file(file_path)
                self.sample_cache[file_path] = samples
            samples = self.sample_cache[file_path]
            self.current_samples = samples
            fname = Path(file_path).name
            self.chart.set_samples(samples, fname, self.events_for_file(fname))
            self.current_range_result = None
            self.range_result_label.setText("Enable Range Analysis, then drag horizontally across the chart.")
            self.refresh_range_mode()
            self.populate_chart_event_table(fname)
            self.update_zoom_text_from_samples()
            # Keep the combo in sync without re-entering this function.
            for i in range(self.chart_file_combo.count()):
                if self.chart_file_combo.itemData(i) == file_path:
                    self.chart_file_combo.blockSignals(True)
                    self.chart_file_combo.setCurrentIndex(i)
                    self.chart_file_combo.blockSignals(False)
                    break
            self.status.setText(f"Chart: {fname}")
        except Exception as e:
            self.log_msg(str(e))

    def on_chart_file_changed(self, index: int = -1) -> None:
        file_path = self.chart_file_combo.currentData()
        if file_path:
            self.load_chart_file(str(file_path))

    def reload_current_chart_file(self) -> None:
        file_path = self.chart_file_combo.currentData()
        if file_path:
            self.load_chart_file(str(file_path), force_reload=True)

    def on_result_selected(self) -> None:
        row = self.result_table.currentRow()
        if row < 0 or row >= len(self.results): return
        fname = self.results[row].file_name
        match = next((f for f in self.files if Path(f).name == fname), None)
        if match:
            self.load_chart_file(match)
            self.tabs.setCurrentIndex(2)

    def set_all_chart_items(self) -> None:
        checked = self.cb_all.isChecked()
        boxes = [self.cb_do, self.cb_vac, self.cb_sf, self.cb_pf, self.cb_chiller, self.cb_abs, self.cb_dyn, self.cb_events, self.cb_non_events, self.cb_value_popup]
        for cb in boxes:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self.refresh_chart_options()

    def refresh_chart_options(self) -> None:
        self.chart.show_do = self.cb_do.isChecked()
        self.chart.show_vac = self.cb_vac.isChecked()
        self.chart.show_sf = self.cb_sf.isChecked()
        self.chart.show_primary_flow = self.cb_pf.isChecked()
        self.chart.show_chiller_temp = self.cb_chiller.isChecked()
        self.chart.show_absolute_pressure = self.cb_abs.isChecked()
        self.chart.show_dynamic_pressure = self.cb_dyn.isChecked()
        self.chart.show_event_markers = self.cb_events.isChecked()
        self.chart.show_non_event_labels = self.cb_non_events.isChecked()
        self.chart.show_value_popup = self.cb_value_popup.isChecked()
        self.chart.update()

    def export_csv(self) -> None:
        if not self.results:
            QMessageBox.information(self, APP_NAME, "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export results", "DO_Analysis_Results.csv", "CSV (*.csv)")
        if not path: return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["File","Type","No","Start","End","Duration","Max DO","Min DO","DO Change","High DO Vac","Low DO Vac","Diff","Trend","2nd Flow Avg","Note"])
            for item in self.results:
                writer.writerow([item.file_name,item.event_type,item.event_no,item.start_time,item.end_time,item.duration_min,item.max_do,item.min_do,item.do_change,item.high_do_vac,item.low_do_vac,item.vac_diff,item.vacuum_trend,item.second_flow_avg,item.note])
        self.log_msg(f"Exported: {path}")

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save project", "DO_Analysis_Project.json", "JSON (*.json)")
        if not path: return
        data = {"version": APP_VERSION, "files": self.files, "hp_master": self.hp_text.toPlainText(), "replacement_history": self.repl_text.toPlainText(), "settings": {"min_do_change": self.sp_min_do.value(), "do_band": self.sp_band.value(), "flat_tol": self.sp_flat.value(), "show_do": self.cb_do.isChecked(), "show_vacuum": self.cb_vac.isChecked(), "show_second_flow": self.cb_sf.isChecked(), "show_primary_flow": self.cb_pf.isChecked(), "show_chiller_temp": self.cb_chiller.isChecked(), "show_absolute_pressure": self.cb_abs.isChecked(), "show_dynamic_pressure": self.cb_dyn.isChecked(), "show_events": self.cb_events.isChecked(), "show_non_events": self.cb_non_events.isChecked(), "show_value_popup": self.cb_value_popup.isChecked()}}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log_msg(f"Saved project: {path}")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load project", "", "JSON (*.json)")
        if not path: return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.files = data.get("files", [])
        self.hp_text.setPlainText(data.get("hp_master", ""))
        self.repl_text.setPlainText(data.get("replacement_history", ""))
        st = data.get("settings", {})
        self.sp_min_do.setValue(float(st.get("min_do_change", MIN_DO_CHANGE_FOR_VACUUM)))
        self.sp_band.setValue(float(st.get("do_band", DO_AVG_BAND)))
        self.sp_flat.setValue(float(st.get("flat_tol", VACUUM_FLAT_TOLERANCE)))
        self.cb_do.setChecked(bool(st.get("show_do", True)))
        self.cb_vac.setChecked(bool(st.get("show_vacuum", True)))
        self.cb_sf.setChecked(bool(st.get("show_second_flow", True)))
        self.cb_pf.setChecked(bool(st.get("show_primary_flow", False)))
        self.cb_chiller.setChecked(bool(st.get("show_chiller_temp", False)))
        self.cb_abs.setChecked(bool(st.get("show_absolute_pressure", False)))
        self.cb_dyn.setChecked(bool(st.get("show_dynamic_pressure", False)))
        self.cb_events.setChecked(bool(st.get("show_events", True)))
        self.cb_non_events.setChecked(bool(st.get("show_non_events", False)))
        self.cb_value_popup.setChecked(bool(st.get("show_value_popup", True)))
        self.cb_all.blockSignals(True)
        self.cb_all.setChecked(all([self.cb_do.isChecked(), self.cb_vac.isChecked(), self.cb_sf.isChecked(), self.cb_pf.isChecked(), self.cb_chiller.isChecked(), self.cb_abs.isChecked(), self.cb_dyn.isChecked(), self.cb_events.isChecked(), self.cb_non_events.isChecked(), self.cb_value_popup.isChecked()]))
        self.cb_all.blockSignals(False)
        self.sample_cache.clear()
        self.populate_chart_file_combo()
        if self.files:
            self.load_chart_file(self.files[0])
        self.refresh_chart_options()
        self.log_msg(f"Loaded project: {path}")

    def create_forecast(self) -> None:
        text = self.repl_text.toPlainText().strip()
        if not text:
            self.forecast_text.setPlainText("No replacement history. Paste or import CSV text first.")
            return
        rows = list(csv.DictReader(text.splitlines()))
        failure = [r for r in rows if r.get("Type", "").strip().lower().startswith("fail")]
        preventive = [r for r in rows if r.get("Type", "").strip().lower().startswith("prev")]
        out = []
        out.append("Simple Forecast Summary")
        out.append(f"Failure replacements only: {len(failure)}")
        out.append(f"Failure + preventive replacements: {len(failure) + len(preventive)}")
        by_hp: Dict[str, int] = {}
        for r in failure:
            hp = r.get("HP", "Unknown") or "Unknown"
            by_hp[hp] = by_hp.get(hp, 0) + 1
        out.append("\nFailure count by HP:")
        for hp, cnt in sorted(by_hp.items(), key=lambda x: (-x[1], x[0])):
            out.append(f"  {hp}: {cnt}")
        self.forecast_text.setPlainText("\n".join(out))


def main() -> int:
    from insightec_handoff import load_handoff
    handoff = load_handoff("do_analysis")
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    if handoff and handoff.auto_load:
        paths = [str(path) for path in handoff.input_paths()]
        if not paths and handoff.workspace():
            paths = [str(handoff.workspace())]
        handoff.mark("do_analysis", "accepted", input_count=len(paths))
        if paths:
            QTimer.singleShot(0, lambda values=paths: w.import_paths(values))
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
