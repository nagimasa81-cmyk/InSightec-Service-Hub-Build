"""Spectrum Dump analysis for Sonication Investigation.

Spectrum_*.dmp_FFT files are gzip-compressed proprietary binary dumps.
This module:
- reads stable header fields confirmed from the supplied sample,
- extracts plausible contiguous float32 spectrum blocks conservatively,
- never exposes the dump as normal Log Viewer rows,
- links the dump to Acquisition log lines by dump filename/time.
"""
from __future__ import annotations

import gzip
import math
import re
import shutil
import tempfile
import zipfile
import struct
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QProgressDialog, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QSlider, QGroupBox, QSpinBox,
    QHeaderView,
)

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

SPECTRUM_NAME_RE = re.compile(
    r"^Spectrum_(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)_"
    r"(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)_"
    r"(?P<day>\d{1,2})_(?P<hour>\d{1,2})_(?P<minute>\d{1,2})_"
    r"(?P<second>\d{1,2})_(?P<year>20\d{2})\.dmp_FFT$",
    re.I,
)

TIME_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2}):(?P<ms>\d{3})")


@dataclass
class SpectrumDump:
    path: Path
    timestamp: datetime | None
    cycle_count: int = 0
    spectrum_count: int = 0
    hydrophone_count: int = 0
    fft_size: int = 0
    averaging_count: int = 0
    sample_rate_hz: int = 0
    reference_hydrophone: int = -1
    acoustic_power: float = 0.0
    main_frequency_hz: float = 0.0
    hydrophone_parameters: list[float] = field(default_factory=list)
    extra_scalar: float = 0.0
    blocks: list[list[float]] = field(default_factory=list)
    decode_mode: str = "Header only"
    acquisition_file: str = ""
    acquisition_line: int = 0
    acquisition_message: str = ""
    acquisition_start: datetime | None = None

    @property
    def nyquist_hz(self) -> float:
        return max(1.0, self.sample_rate_hz / 2.0)

    def peak(self, block_index: int) -> tuple[float, float]:
        if not (0 <= block_index < len(self.blocks)):
            return 0.0, 0.0
        values = self.blocks[block_index]
        if not values:
            return 0.0, 0.0
        peak_index = max(range(len(values)), key=lambda i: values[i])
        frequency = peak_index * self.nyquist_hz / max(1, len(values) - 1)
        return frequency, values[peak_index]



def is_spectrum_dump(path: Path) -> bool:
    """Case-insensitive and suffix-tolerant Spectrum Dump detection."""
    name = path.name.lower()
    return (
        name.startswith("spectrum_")
        and (
            name.endswith(".dmp_fft")
            or name.endswith(".dmp.fft")
            or name.endswith("_dmp_fft")
            or ".dmp_fft." in name
        )
    )


def _safe_cache_name(prefix: str, member_name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(member_name).name)
    return f"{prefix}_{clean}"


def _extract_spectrum_members_from_zip(
    zip_path: Path,
    cache_dir: Path,
    found: dict[str, Path],
    diagnostics: dict[str, int],
    nested_depth: int = 0,
) -> None:
    """Extract Spectrum Dump members from ZIPs.

    One nested ZIP level is supported because field packages often contain a
    site ZIP which itself contains the raw-log ZIP.
    """
    if nested_depth > 1:
        return

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            diagnostics["zip_files_scanned"] += 1
            for member in archive.infolist():
                if member.is_dir():
                    continue

                diagnostics["zip_members_scanned"] += 1
                member_path = Path(member.filename)

                if is_spectrum_dump(member_path):
                    target = cache_dir / _safe_cache_name(
                        f"z{diagnostics['zip_files_scanned']}",
                        member.filename,
                    )
                    with archive.open(member, "r") as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                    key = f"{zip_path.resolve()}!{member.filename}".casefold()
                    found[key] = target
                    diagnostics["spectrum_found"] += 1
                    continue

                if member_path.name.lower().endswith(".zip"):
                    try:
                        nested_target = cache_dir / _safe_cache_name(
                            f"nested{diagnostics['zip_files_scanned']}",
                            member.filename,
                        )
                        nested_target.write_bytes(archive.read(member))
                        _extract_spectrum_members_from_zip(
                            nested_target,
                            cache_dir,
                            found,
                            diagnostics,
                            nested_depth + 1,
                        )
                    except Exception:
                        diagnostics["errors"] += 1
    except Exception:
        diagnostics["errors"] += 1


def find_spectrum_dumps(
    paths: list[Path],
    cache_dir: Path | None = None,
) -> tuple[list[Path], dict[str, int]]:
    """Search loaded files, folders and ZIP contents for Spectrum Dumps."""
    found: dict[str, Path] = {}
    diagnostics = {
        "input_paths": len(paths),
        "filesystem_files_scanned": 0,
        "zip_files_scanned": 0,
        "zip_members_scanned": 0,
        "spectrum_found": 0,
        "errors": 0,
    }

    cache_dir = Path(cache_dir or tempfile.mkdtemp(prefix="spectrum_cache_"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    def inspect_file(path: Path) -> None:
        try:
            diagnostics["filesystem_files_scanned"] += 1
            if is_spectrum_dump(path):
                found[str(path.resolve()).casefold()] = path
                diagnostics["spectrum_found"] += 1
            elif path.suffix.lower() == ".zip":
                _extract_spectrum_members_from_zip(
                    path,
                    cache_dir,
                    found,
                    diagnostics,
                )
        except Exception:
            diagnostics["errors"] += 1

    for value in paths:
        path = Path(value)
        if not path.exists():
            diagnostics["errors"] += 1
            continue

        if path.is_file():
            inspect_file(path)
            continue

        try:
            for candidate in path.rglob("*"):
                if candidate.is_file():
                    inspect_file(candidate)
        except Exception:
            diagnostics["errors"] += 1

    ordered = sorted(
        found.values(),
        key=lambda item: (
            spectrum_timestamp(item) or datetime.min,
            str(item).casefold(),
        ),
    )
    return ordered, diagnostics


def spectrum_timestamp(path: Path) -> datetime | None:
    match = SPECTRUM_NAME_RE.match(path.name)
    if not match:
        return None
    try:
        return datetime(
            int(match.group("year")),
            MONTHS[match.group("mon").title()],
            int(match.group("day")),
            int(match.group("hour")),
            int(match.group("minute")),
            int(match.group("second")),
        )
    except Exception:
        return None


def _safe_int(data: bytes, offset: int, default: int = 0) -> int:
    try:
        return int(struct.unpack_from("<i", data, offset)[0])
    except Exception:
        return default


def _safe_double(data: bytes, offset: int, default: float = 0.0) -> float:
    try:
        value = float(struct.unpack_from("<d", data, offset)[0])
        return value if math.isfinite(value) else default
    except Exception:
        return default


def _float_runs(data: bytes, offset: int, maximum_blocks: int) -> list[list[float]]:
    """Extract conservative positive finite float32 runs.

    The supplied dump contains repeated contiguous numeric regions separated by
    proprietary metadata. Runs between 256 and 32768 points are candidates.
    The longest candidates are used as Hydrophone spectra.
    """
    usable = len(data) - ((len(data) - offset) % 4)
    candidates: list[list[float]] = []
    current: list[float] = []

    for position in range(offset, usable, 4):
        try:
            value = float(struct.unpack_from("<f", data, position)[0])
        except Exception:
            value = float("nan")

        plausible = (
            math.isfinite(value)
            and 0.0 <= value <= 1_000_000.0
        )

        if plausible:
            current.append(value)
        else:
            if 256 <= len(current) <= 32768:
                candidates.append(current)
            current = []

    if 256 <= len(current) <= 32768:
        candidates.append(current)

    # Prefer substantial repeated blocks. Similar-length blocks usually
    # represent the configured Hydrophones in the supplied format.
    candidates.sort(key=lambda block: len(block), reverse=True)
    selected = candidates[:maximum_blocks]

    # Avoid huge UI payloads while preserving the envelope.
    output: list[list[float]] = []
    for block in selected:
        if len(block) <= 4096:
            output.append(block)
            continue
        step = len(block) / 4096.0
        reduced = [
            block[min(len(block) - 1, int(index * step))]
            for index in range(4096)
        ]
        output.append(reduced)
    return output


def parse_spectrum_dump(path: Path) -> SpectrumDump:
    timestamp = spectrum_timestamp(path)
    result = SpectrumDump(path=path, timestamp=timestamp)

    try:
        raw = gzip.decompress(path.read_bytes())
    except Exception:
        raw = path.read_bytes()

    if len(raw) < 144:
        return result

    result.cycle_count = _safe_int(raw, 0)
    result.spectrum_count = _safe_int(raw, 4)
    result.hydrophone_count = max(0, _safe_int(raw, 8))
    result.fft_size = max(0, _safe_int(raw, 12))
    result.averaging_count = max(0, _safe_int(raw, 16))
    result.sample_rate_hz = max(0, _safe_int(raw, 20))
    result.reference_hydrophone = _safe_int(raw, 24)
    result.acoustic_power = _safe_double(raw, 24)
    result.main_frequency_hz = _safe_double(raw, 32)
    result.hydrophone_parameters = [
        _safe_double(raw, 40 + index * 8)
        for index in range(min(8, max(0, result.hydrophone_count)))
    ]
    result.extra_scalar = _safe_double(raw, 104)

    block_count = result.hydrophone_count if 1 <= result.hydrophone_count <= 16 else 8
    result.blocks = _float_runs(raw, 144, block_count)
    result.decode_mode = (
        "Header + heuristic spectrum blocks"
        if result.blocks
        else "Header only"
    )
    return result


def link_acquisition(dump: SpectrumDump, root: Path, recursive: bool) -> None:
    if dump.timestamp is None or not root.exists():
        return

    iterator = root.rglob("Acquisition_*.txt") if recursive else root.glob("Acquisition_*.txt")
    target_names = {
        dump.path.name.lower(),
        dump.path.name.replace(".dmp_FFT", ".dmp").lower(),
    }

    best: tuple[float, Path, int, str, datetime | None] | None = None
    for log_path in iterator:
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        current_date = dump.timestamp.date()
        for line_number, line in enumerate(lines, 1):
            lower = line.lower()
            exact = any(name in lower for name in target_names)

            match = TIME_RE.match(line.strip())
            line_time = None
            if match:
                try:
                    line_time = datetime(
                        current_date.year, current_date.month, current_date.day,
                        int(match.group("h")), int(match.group("m")),
                        int(match.group("s")), int(match.group("ms")) * 1000,
                    )
                except Exception:
                    line_time = None

            if exact:
                diff = 0.0
            elif line_time is not None and "saving fft data" in lower:
                diff = abs((line_time - dump.timestamp).total_seconds())
                if diff > 10:
                    continue
            else:
                continue

            start_time = None
            for previous in range(max(0, line_number - 5000), line_number - 1):
                previous_line = lines[previous]
                if "StartSpectrumMeasurementA" in previous_line:
                    time_match = TIME_RE.match(previous_line.strip())
                    if time_match:
                        start_time = datetime(
                            current_date.year, current_date.month, current_date.day,
                            int(time_match.group("h")), int(time_match.group("m")),
                            int(time_match.group("s")), int(time_match.group("ms")) * 1000,
                        )

            candidate = (diff, log_path, line_number, line.strip(), start_time)
            if best is None or candidate[0] < best[0]:
                best = candidate

    if best:
        dump.acquisition_file = best[1].name
        dump.acquisition_line = best[2]
        dump.acquisition_message = best[3]
        dump.acquisition_start = best[4]


class SpectrumPlot(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.dump: SpectrumDump | None = None
        self.visible: set[int] = set()
        self.log_scale = False
        self.mode = "Spectrum Overlay"
        self.compare_dump: SpectrumDump | None = None
        self.replay_fraction = 1.0
        self.domain = "Frequency Data"
        self.crosshair_pos = None
        self.drag_start = None
        self.drag_current = None
        self.zoom_rect = None
        self.selected_bands = [0]
        self.setMouseTracking(True)
        self.setMinimumHeight(360)

    def set_dump(self, dump: SpectrumDump | None) -> None:
        self.dump = dump
        self.visible = set(range(len(dump.blocks))) if dump else set()
        self.update()

    def _converted_blocks(self, dump: SpectrumDump) -> list[tuple[int, list[float]]]:
        output = []
        for index in sorted(self.visible):
            if index >= len(dump.blocks):
                continue
            values = dump.blocks[index]
            if self.log_scale:
                plotted = [math.log10(max(value, 1e-12)) for value in values]
                baseline = min(plotted, default=0.0)
                plotted = [value - baseline for value in plotted]
            else:
                plotted = list(values)
            output.append((index, plotted))
        return output

    def reset_zoom(self):
        self.zoom_rect = None
        self.update()

    def mouseMoveEvent(self, event):
        self.crosshair_pos = event.position()
        if self.drag_start is not None:
            self.drag_current = event.position()
        self.update()

    def leaveEvent(self, event):
        self.crosshair_pos = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = event.position()
            self.drag_current = event.position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_start is not None:
            end = event.position()
            rect = QRectF(self.drag_start, end).normalized()
            if rect.width() > 12 and rect.height() > 12:
                self.zoom_rect = QRectF(rect)
            self.drag_start = None
            self.drag_current = None
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.reset_zoom()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        plot = self.rect().adjusted(70, 30, -24, -55)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRect(plot)

        if self.dump is None or not self.dump.blocks:
            painter.setPen(QColor("#64748B"))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Select a Spectrum Dump.\nSpectrum Dumps are not shown in Log Viewer.",
            )
            return

        palette = [
            QColor("#005DAA"), QColor("#D97706"), QColor("#059669"),
            QColor("#7C3AED"), QColor("#DC2626"), QColor("#0891B2"),
            QColor("#9333EA"), QColor("#4D7C0F"),
        ]
        converted = self._converted_blocks(self.dump)
        if not converted:
            return

        if self.mode == "Energy per Band":
            selected_bands = self.selected_bands or [0]
            transformed = []
            for block_index, values in converted:
                if not values:
                    transformed.append((block_index, []))
                    continue
                band_size = max(1, len(values) // 6)
                output = []
                for sample_index, value in enumerate(values):
                    band_index = min(5, sample_index // band_size)
                    output.append(abs(value) if band_index in selected_bands else 0.0)
                transformed.append((block_index, output))
            converted = transformed

        if self.mode in {"Heatmap", "Waterfall"}:
            row_height = plot.height() / max(1, len(converted))
            global_max = max(
                (max(values, default=0.0) for _, values in converted),
                default=1.0,
            ) or 1.0

            for row, (block_index, values) in enumerate(converted):
                if not values:
                    continue
                y_top = plot.top() + row * row_height

                if self.mode == "Heatmap":
                    columns = min(512, len(values))
                    for column in range(columns):
                        source_index = int(column * len(values) / columns)
                        ratio = max(0.0, min(1.0, values[source_index] / global_max))
                        color = QColor.fromHsvF(
                            max(0.0, 0.66 - ratio * 0.66),
                            0.85,
                            0.95,
                        )
                        x = plot.left() + column * plot.width() / columns
                        painter.fillRect(
                            QRectF(
                                x,
                                y_top,
                                plot.width() / columns + 1,
                                row_height + 1,
                            ),
                            color,
                        )
                else:
                    painter.setPen(QPen(palette[block_index % len(palette)], 1.0))
                    offset = row * row_height
                    maximum = max(values, default=1.0) or 1.0
                    previous = None
                    for point_index, value in enumerate(values):
                        x = (
                            plot.left()
                            + point_index * plot.width() / max(1, len(values) - 1)
                        )
                        y = (
                            plot.top()
                            + offset
                            + row_height
                            - (value / maximum) * row_height * 0.82
                        )
                        point = QPointF(x, y)
                        if previous is not None:
                            painter.drawLine(previous, point)
                        previous = point

                painter.setPen(QColor("#334155"))
                painter.drawText(
                    8,
                    int(y_top + min(row_height - 2, 16)),
                    f"H{block_index}",
                )

        else:
            all_series = list(converted)
            if self.mode == "FFT Compare" and self.compare_dump is not None:
                for block_index, values in enumerate(self.compare_dump.blocks[:2]):
                    all_series.append((block_index + 100, values))

            maximum = max(
                (max(values, default=0.0) for _, values in all_series),
                default=1.0,
            ) or 1.0

            replay_points = None
            if self.mode == "Sonication Replay":
                replay_points = max(
                    2,
                    int(
                        max(len(values) for _, values in all_series)
                        * max(0.01, self.replay_fraction)
                    ),
                )

            for series_index, (block_index, values) in enumerate(all_series):
                if replay_points is not None:
                    values = values[:replay_points]
                if len(values) < 2:
                    continue

                if block_index >= 100:
                    pen = QPen(QColor("#111827"), 1.0, Qt.DashLine)
                else:
                    pen = QPen(palette[block_index % len(palette)], 1.2)
                painter.setPen(pen)

                previous = None
                for point_index, value in enumerate(values):
                    x = (
                        plot.left()
                        + point_index * plot.width() / max(1, len(values) - 1)
                    )
                    y = plot.bottom() - (value / maximum) * plot.height()
                    point = QPointF(x, y)
                    if previous is not None:
                        painter.drawLine(previous, point)
                    previous = point

            if self.mode == "Harmonics":
                fundamental = self.dump.main_frequency_hz
                if fundamental > 0:
                    for harmonic in range(1, 7):
                        frequency = fundamental * harmonic
                        if frequency >= self.dump.nyquist_hz:
                            break
                        x = (
                            plot.left()
                            + frequency / self.dump.nyquist_hz * plot.width()
                        )
                        painter.setPen(
                            QPen(
                                QColor("#EF4444") if harmonic == 1 else QColor("#F59E0B"),
                                1.2,
                                Qt.DashLine,
                            )
                        )
                        painter.drawLine(
                            QPointF(x, plot.top()),
                            QPointF(x, plot.bottom()),
                        )
                        painter.drawText(
                            int(x + 3),
                            plot.top() + 14 + 13 * (harmonic % 2),
                            f"{harmonic}×",
                        )

        if 0 < self.dump.main_frequency_hz < self.dump.nyquist_hz:
            x = (
                plot.left()
                + self.dump.main_frequency_hz / self.dump.nyquist_hz
                * plot.width()
            )
            painter.setPen(QPen(QColor("#EF4444"), 1.2, Qt.DashLine))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

        painter.setPen(QColor("#475569"))
        painter.drawText(plot.left(), self.height() - 18, "0 Hz")
        painter.drawText(
            plot.right() - 85,
            self.height() - 18,
            f"{self.dump.nyquist_hz / 1_000_000:.3f} MHz",
        )
        axis_label = "Energy" if self.mode == "Energy per Band" else "Amplitude"
        painter.drawText(8, plot.top() + 15, axis_label)

        # Axis ticks.
        painter.setPen(QColor("#64748B"))
        for tick in range(6):
            ratio = tick / 5.0
            x = plot.left() + ratio * plot.width()
            painter.drawLine(QPointF(x, plot.bottom()), QPointF(x, plot.bottom() + 4))
            frequency = ratio * self.dump.nyquist_hz
            painter.drawText(int(x - 28), plot.bottom() + 18, f"{frequency/1000:.0f}k")
            y = plot.bottom() - ratio * plot.height()
            painter.drawLine(QPointF(plot.left() - 4, y), QPointF(plot.left(), y))
            painter.drawText(8, int(y + 4), f"{ratio:.1f}")

        # Crosshair and coordinate display.
        if self.crosshair_pos is not None and QRectF(plot).contains(self.crosshair_pos):
            pos = self.crosshair_pos
            painter.setPen(QPen(QColor("#334155"), 1, Qt.DashLine))
            painter.drawLine(QPointF(pos.x(), plot.top()), QPointF(pos.x(), plot.bottom()))
            painter.drawLine(QPointF(plot.left(), pos.y()), QPointF(plot.right(), pos.y()))
            x_ratio = (pos.x() - plot.left()) / max(1.0, plot.width())
            y_ratio = (plot.bottom() - pos.y()) / max(1.0, plot.height())
            frequency = x_ratio * self.dump.nyquist_hz
            painter.setPen(QColor("#111827"))
            painter.drawText(
                int(min(plot.right() - 210, pos.x() + 8)),
                int(max(plot.top() + 16, pos.y() - 8)),
                f"{frequency/1000:.3f} kHz | Y {y_ratio:.5f}",
            )

        if self.drag_start is not None and self.drag_current is not None:
            painter.setPen(QPen(QColor("#005DAA"), 1, Qt.DashLine))
            painter.drawRect(QRectF(self.drag_start, self.drag_current).normalized())

        painter.drawText(
            plot.left() + 8,
            plot.top() + 18,
            f"{self.mode} | {self.domain}",
        )


class SpectrumAnalysisWidget(QWidget):
    def __init__(self, investigation: Any = None, standalone: bool = False):
        super().__init__(investigation)
        self.investigation = investigation
        self.standalone = standalone
        self.explicit_paths: list[Path] = []
        self._cache_holder = tempfile.TemporaryDirectory(
            prefix="logmerge_spectrum_"
        )
        self.cache_dir = Path(self._cache_holder.name)
        self.dumps: list[SpectrumDump] = []
        self.checks: list[QCheckBox] = []
        self.setAcceptDrops(True)
        self._build_ui()

    def source_paths(self) -> list[Path]:
        if self.explicit_paths:
            return list(self.explicit_paths)

        if self.investigation is None:
            return []

        viewer = getattr(self.investigation, "viewer", None)
        parent = getattr(viewer, "parent_window", None)
        paths: list[Path] = []

        selected = getattr(parent, "viewer_selected_files", []) or []
        for value in selected:
            path = Path(value)
            if path.exists():
                paths.append(path)

        edit = getattr(parent, "source_edit", None)
        if edit is not None:
            value = edit.text().strip()
            if value:
                path = Path(value)
                if path.exists():
                    paths.append(path)

        # Deduplicate while keeping order.
        output = []
        seen = set()
        for path in paths:
            key = str(path.resolve()).casefold()
            if key not in seen:
                seen.add(key)
                output.append(path)
        return output

    def source_root(self) -> Path:
        paths = self.source_paths()
        if not paths:
            return Path(".")
        first = paths[0]
        return first if first.is_dir() else first.parent

    def recursive(self) -> bool:
        return True

    def load_paths(self, values) -> None:
        self.explicit_paths = [Path(value) for value in values]
        self.reload()

    def use_loaded_sources(self) -> None:
        self.explicit_paths = []
        self.reload()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        title = QLabel("Spectrum Analysis")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#005DAA;")
        reload_button = QPushButton("Scan Spectrum Dumps")
        reload_button.clicked.connect(self.reload)
        self.domain = QComboBox()
        self.domain.addItems(["Frequency Data", "Raw / Reconstructed Data"])
        self.domain.currentTextChanged.connect(self._domain_changed)

        self.scale = QComboBox()
        self.scale.addItems(["Linear", "Log"])
        self.scale.currentTextChanged.connect(self._scale_changed)

        self.display_mode = QComboBox()
        self.display_mode.addItems([
            "Spectrum Overlay",
            "Waterfall",
            "Heatmap",
            "Harmonics",
            "FFT Compare",
            "Sonication Replay",
        ])
        self.display_mode.currentTextChanged.connect(self._mode_changed)

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QLabel("Domain:"))
        top.addWidget(self.domain)
        top.addWidget(QLabel("Display:"))
        top.addWidget(self.display_mode)
        top.addWidget(QLabel("Scale:"))
        top.addWidget(self.scale)
        top.addWidget(reload_button)
        root.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Spectrum Dumps"))
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.select_dump)
        left_layout.addWidget(self.file_list, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.summary = QLabel("No Spectrum Dump selected.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "background:#EAF2F8;border:1px solid #CBD5E1;"
            "border-radius:4px;padding:8px;"
        )
        right_layout.addWidget(self.summary)

        navigator = QHBoxLayout()
        navigator.addWidget(QLabel("Measure #"))
        self.measure_spin = QSpinBox()
        self.measure_spin.setRange(1, 1)
        self.measure_spin.valueChanged.connect(self._measure_changed)
        self.first_button = QPushButton("|<")
        self.previous_button = QPushButton("<")
        self.next_button = QPushButton(">")
        self.last_button = QPushButton(">|")
        self.first_button.clicked.connect(lambda: self.measure_spin.setValue(1))
        self.previous_button.clicked.connect(
            lambda: self.measure_spin.setValue(
                max(1, self.measure_spin.value() - 1)
            )
        )
        self.next_button.clicked.connect(
            lambda: self.measure_spin.setValue(
                min(self.measure_spin.maximum(), self.measure_spin.value() + 1)
            )
        )
        self.last_button.clicked.connect(
            lambda: self.measure_spin.setValue(self.measure_spin.maximum())
        )
        self.measure_status = QLabel("out of <0> saved measurements")
        navigator.addWidget(self.measure_spin)
        navigator.addWidget(self.measure_status)
        navigator.addWidget(self.first_button)
        navigator.addWidget(self.previous_button)
        navigator.addWidget(self.next_button)
        navigator.addWidget(self.last_button)
        navigator.addStretch(1)
        right_layout.addLayout(navigator)

        save_controls = QHBoxLayout()
        save_controls.addWidget(QLabel("Save Spectrum Data:"))
        self.save_all = QPushButton("All")
        self.save_auto = QPushButton("Auto")
        self.save_none = QPushButton("None")
        self.save_auto.setCheckable(True)
        self.save_auto.setChecked(True)
        self.save_all.clicked.connect(self._select_all_hydrophones)
        self.save_none.clicked.connect(self._select_no_hydrophones)
        save_controls.addWidget(self.save_all)
        save_controls.addWidget(self.save_auto)
        save_controls.addWidget(self.save_none)
        save_controls.addStretch(1)
        right_layout.addLayout(save_controls)

        self.hydro_controls = QHBoxLayout()
        self.hydro_controls.addWidget(QLabel("Channels:"))
        self.hydro_all = QPushButton("Select All")
        self.hydro_none = QPushButton("Select None")
        self.reset_zoom_button = QPushButton("Reset Zoom")
        self.hydro_all.clicked.connect(self._select_all_hydrophones)
        self.hydro_none.clicked.connect(self._select_no_hydrophones)
        self.reset_zoom_button.clicked.connect(self._reset_zoom)
        self.hydro_controls.addWidget(self.hydro_all)
        self.hydro_controls.addWidget(self.hydro_none)
        self.hydro_controls.addWidget(self.reset_zoom_button)
        self.hydro_controls.addStretch(1)
        right_layout.addLayout(self.hydro_controls)

        analysis_controls = QHBoxLayout()
        self.compare_combo = QComboBox()
        self.compare_combo.setToolTip("Select another FFT Dump for dashed comparison.")
        self.compare_combo.currentIndexChanged.connect(self._compare_changed)
        self.replay_slider = QSlider(Qt.Horizontal)
        self.replay_slider.setRange(1, 100)
        self.replay_slider.setValue(100)
        self.replay_slider.valueChanged.connect(self._replay_changed)
        self.replay_play = QPushButton("Play Replay")
        self.replay_play.clicked.connect(self._toggle_replay)
        analysis_controls.addWidget(QLabel("Compare:"))
        analysis_controls.addWidget(self.compare_combo, 1)
        analysis_controls.addWidget(QLabel("Replay:"))
        analysis_controls.addWidget(self.replay_slider, 1)
        analysis_controls.addWidget(self.replay_play)
        right_layout.addLayout(analysis_controls)

        self.replay_timer = QTimer(self)
        self.replay_timer.setInterval(80)
        self.replay_timer.timeout.connect(self._replay_tick)

        self.energy_plot = SpectrumPlot()
        self.energy_plot.mode = "Energy per Band"
        self.energy_plot.setMinimumHeight(180)

        self.plot = SpectrumPlot()
        self.plot.mode = "Raw Data from A2D"
        self.plot.setMinimumHeight(280)

        self.frequency_plot = SpectrumPlot()
        self.frequency_plot.mode = "Spectrum"
        self.frequency_plot.domain = "Frequency Data"
        self.frequency_plot.setMinimumHeight(240)

        self.plot_splitter = QSplitter(Qt.Vertical)
        self.plot_splitter.addWidget(self.energy_plot)
        self.plot_splitter.addWidget(self.plot)
        self.plot_splitter.addWidget(self.frequency_plot)
        self.plot_splitter.setStretchFactor(0, 1)
        self.plot_splitter.setStretchFactor(1, 2)
        self.plot_splitter.setStretchFactor(2, 2)
        self.plot_splitter.setSizes([190, 320, 280])
        right_layout.addWidget(self.plot_splitter, 1)

        band_bar = QHBoxLayout()
        band_bar.addWidget(QLabel("Bands:"))
        self.band_checks = []
        for band_index in range(6):
            check = QCheckBox(f"#{band_index}")
            check.setChecked(band_index == 0)
            check.toggled.connect(self._band_selection_changed)
            self.band_checks.append(check)
            band_bar.addWidget(check)
        band_bar.addStretch(1)
        right_layout.addLayout(band_bar)

        self.packet_table = QTableWidget(0, 8)
        self.packet_table.setHorizontalHeaderLabels(
            [
                "Channel",
                "Packet Validity",
                "Sonic State",
                "Points",
                "Peak Frequency",
                "Peak Amplitude",
                "Band Energy",
                "Candidate",
            ]
        )
        self.packet_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.packet_table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.Stretch
        )
        self.packet_table.setMaximumHeight(210)
        right_layout.addWidget(self.packet_table)

        # Backward-compatible alias used by older code paths.
        self.peaks = self.packet_table

        splitter.addWidget(right)
        splitter.setSizes([280, 1000])

    def reload(self) -> None:
        root = self.source_root()
        search_paths = self.source_paths()
        if not search_paths:
            self.plot.set_dump(None)
            self.energy_plot.set_dump(None)
            self.frequency_plot.set_dump(None)
            self.summary.setText(
                "No loaded source is available. Load a folder/ZIP in the main "
                "screen, or use the standalone Spectrum Analysis buttons."
            )
            return

        paths, diagnostics = find_spectrum_dumps(
            search_paths,
            self.cache_dir,
        )

        progress = QProgressDialog(
            "Scanning Spectrum Dumps...", "Cancel", 0, max(1, len(paths)), self
        )
        progress.setWindowTitle("Spectrum Analysis")
        progress.setMinimumDuration(0)
        progress.show()

        dumps: list[SpectrumDump] = []
        for index, path in enumerate(paths, 1):
            if progress.wasCanceled():
                break
            progress.setValue(index - 1)
            progress.setLabelText(f"Reading {index}/{len(paths)}\n{path.name}")
            QApplication.processEvents()
            try:
                dump = parse_spectrum_dump(path)
                if root.exists() and root.is_dir():
                    link_acquisition(dump, root, self.recursive())
                dumps.append(dump)
            except Exception:
                continue

        progress.setValue(len(paths))
        progress.close()

        self.dumps = dumps
        self.file_list.clear()
        self.compare_combo.blockSignals(True)
        self.compare_combo.clear()
        self.compare_combo.addItem("None", -1)
        for compare_index, compare_dump in enumerate(dumps):
            self.compare_combo.addItem(compare_dump.path.name, compare_index)
        self.compare_combo.blockSignals(False)

        for dump in dumps:
            time_text = dump.timestamp.strftime("%Y/%m/%d %H:%M:%S") if dump.timestamp else ""
            item = QListWidgetItem(
                f"{time_text}\n{dump.path.name}\n"
                f"{dump.acoustic_power:g} W / "
                f"{dump.main_frequency_hz / 1_000_000:.3f} MHz"
            )
            self.file_list.addItem(item)

        if dumps:
            self.file_list.setCurrentRow(0)
            self.summary.setText(
                f"Detected {len(dumps):,} Spectrum Dump(s) from the loaded "
                f"source. Files scanned: "
                f"{diagnostics['filesystem_files_scanned']:,}; ZIP files: "
                f"{diagnostics['zip_files_scanned']:,}; ZIP members: "
                f"{diagnostics['zip_members_scanned']:,}."
            )
        else:
            self.plot.set_dump(None)
            self.energy_plot.set_dump(None)
            self.frequency_plot.set_dump(None)
            self.summary.setText(
                "No Spectrum Dump was detected. "
                f"Files scanned: {diagnostics['filesystem_files_scanned']:,}; "
                f"ZIP files: {diagnostics['zip_files_scanned']:,}; "
                f"ZIP members: {diagnostics['zip_members_scanned']:,}; "
                f"errors: {diagnostics['errors']:,}. "
                "The search is recursive and accepts .dmp_FFT, .dmp.fft, "
                "case variations, ZIP contents and one nested ZIP level."
            )

    def _clear_checks(self) -> None:
        while self.hydro_controls.count() > 2:
            item = self.hydro_controls.takeAt(1)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.checks.clear()

    def select_dump(self, index: int) -> None:
        if not (0 <= index < len(self.dumps)):
            return
        dump = self.dumps[index]
        self.plot.set_dump(dump)
        self.energy_plot.set_dump(dump)
        self.frequency_plot.set_dump(dump)
        self._update_measure_status()
        self._clear_checks()

        for block_index in range(len(dump.blocks)):
            check = QCheckBox(f"H{block_index}")
            check.setChecked(True)
            check.toggled.connect(
                lambda checked, i=block_index: self._toggle_block(i, checked)
            )
            self.hydro_controls.insertWidget(
                max(1, self.hydro_controls.count() - 1), check
            )
            self.checks.append(check)

        linked = (
            f"{dump.acquisition_file}, line {dump.acquisition_line}"
            if dump.acquisition_file
            else "Not linked"
        )
        start = (
            dump.acquisition_start.strftime("%H:%M:%S.%f")[:-3]
            if dump.acquisition_start else "Unknown"
        )
        self.summary.setText(
            f"<b>{dump.path.name}</b><br>"
            f"Timestamp: {dump.timestamp or 'Unknown'} &nbsp; "
            f"Acoustic Power: {dump.acoustic_power:g} W &nbsp; "
            f"Main Frequency: {dump.main_frequency_hz / 1_000_000:.3f} MHz<br>"
            f"Hydrophones: {dump.hydrophone_count} &nbsp; "
            f"FFT Size: {dump.fft_size:,} &nbsp; "
            f"Sample Rate: {dump.sample_rate_hz / 1_000_000:.3f} MHz &nbsp; "
            f"Spectra: {dump.spectrum_count:,}<br>"
            f"Decode: {dump.decode_mode}<br>"
            f"Acquisition link: {linked} &nbsp; Measurement start: {start}<br>"
            f"<b>Cavitation candidate:</b> "
            f"{'Review broadband/subharmonic peaks' if dump.blocks else 'No spectrum block'} "
            f"(analysis-support only)"
        )

        self._update_packet_table(dump)

    def _mode_changed(self, mode: str) -> None:
        # Three reference plots remain visible. The display selector controls
        # the primary raw plot behavior while preserving the reference layout.
        self.plot.mode = (
            "Raw Data from A2D"
            if mode in {"Spectrum Overlay", "Sonication Replay"}
            else mode
        )
        self.energy_plot.mode = "Energy per Band"
        self.frequency_plot.mode = "Spectrum"
        replay_enabled = mode == "Sonication Replay"
        self.replay_slider.setEnabled(replay_enabled)
        self.replay_play.setEnabled(replay_enabled)
        self.plot.update()
        self.energy_plot.update()
        self.frequency_plot.update()

    def _compare_changed(self, combo_index: int) -> None:
        dump_index = self.compare_combo.itemData(combo_index)
        if isinstance(dump_index, int) and 0 <= dump_index < len(self.dumps):
            compare_dump = self.dumps[dump_index]
        else:
            compare_dump = None
        for target in (self.plot, self.energy_plot, self.frequency_plot):
            target.compare_dump = compare_dump
            target.update()

    def _replay_changed(self, value: int) -> None:
        replay_fraction = max(0.01, value / 100.0)
        for target in (self.plot, self.energy_plot, self.frequency_plot):
            target.replay_fraction = replay_fraction
            target.update()

    def _toggle_replay(self) -> None:
        if self.replay_timer.isActive():
            self.replay_timer.stop()
            self.replay_play.setText("Play Replay")
        else:
            if self.replay_slider.value() >= 100:
                self.replay_slider.setValue(1)
            self.replay_timer.start()
            self.replay_play.setText("Pause Replay")

    def _replay_tick(self) -> None:
        value = self.replay_slider.value() + 2
        if value >= 100:
            value = 100
            self.replay_timer.stop()
            self.replay_play.setText("Play Replay")
        self.replay_slider.setValue(value)

    def _measure_changed(self, value: int) -> None:
        if not self.dumps:
            return
        index = max(0, min(len(self.dumps) - 1, value - 1))
        if self.file_list.currentRow() != index:
            self.file_list.setCurrentRow(index)

    def _update_measure_status(self) -> None:
        total = len(self.dumps)
        self.measure_spin.blockSignals(True)
        self.measure_spin.setMaximum(max(1, total))
        current = max(1, self.file_list.currentRow() + 1)
        self.measure_spin.setValue(current)
        self.measure_spin.blockSignals(False)
        self.measure_status.setText(
            f"out of <{total}> saved measurements"
        )

    def _band_selection_changed(self) -> None:
        selected = [
            index
            for index, check in enumerate(self.band_checks)
            if check.isChecked()
        ]
        self.energy_plot.selected_bands = selected or [0]
        self.energy_plot.update()
        if self.plot.dump is not None:
            self._update_packet_table(self.plot.dump)

    def _update_packet_table(self, dump) -> None:
        blocks = list(getattr(dump, "blocks", []) or [])
        selected_bands = [
            index
            for index, check in enumerate(self.band_checks)
            if check.isChecked()
        ] or [0]

        self.packet_table.setRowCount(len(blocks))
        for row, block in enumerate(blocks):
            frequency, amplitude = dump.peak(row)
            band_size = max(1, len(block) // 6) if block else 1
            energy = 0.0
            for band_index in selected_bands:
                start = band_index * band_size
                end = (
                    len(block)
                    if band_index == 5
                    else min(len(block), (band_index + 1) * band_size)
                )
                energy += sum(abs(value) for value in block[start:end])

            average = (
                sum(abs(value) for value in block) / max(1, len(block))
                if block else 0.0
            )
            peak_ratio = amplitude / max(1e-12, average)
            candidate = (
                "Review"
                if peak_ratio >= 8.0
                else "Moderate"
                if peak_ratio >= 4.0
                else "Low"
            )

            values = [
                f"Ch{row}",
                "Valid" if block else "Invalid",
                "Sonication" if getattr(dump, "acoustic_power", 0) else "Idle",
                f"{len(block):,}",
                f"{frequency / 1_000_000:.6f} MHz",
                f"{amplitude:.8g}",
                f"{energy:.8g}",
                candidate,
            ]
            for column, value in enumerate(values):
                self.packet_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

    def _domain_changed(self, text: str) -> None:
        self.plot.domain = text
        self.energy_plot.domain = "Energy Data"
        self.frequency_plot.domain = "Frequency Data"
        self.plot.update()
        self.energy_plot.update()
        self.frequency_plot.update()
        if text.startswith("Raw") and self.plot.dump is not None:
            self.summary.setText(
                self.summary.text()
                + "<br><b>Raw note:</b> true raw waveform is shown only when "
                  "the dump contains recoverable complex/time-domain data; "
                  "otherwise this is a reconstructed preview."
            )

    def _select_all_hydrophones(self) -> None:
        for check in self.checks:
            check.setChecked(True)

    def _select_no_hydrophones(self) -> None:
        for check in self.checks:
            check.setChecked(False)

    def _reset_zoom(self) -> None:
        self.plot.reset_zoom()
        self.energy_plot.reset_zoom()
        self.frequency_plot.reset_zoom()

    def _toggle_block(self, index: int, checked: bool) -> None:
        for target in (self.plot, self.energy_plot, self.frequency_plot):
            if checked:
                target.visible.add(index)
            else:
                target.visible.discard(index)
            target.update()

    def _scale_changed(self, text: str) -> None:
        for target in (self.plot, self.energy_plot, self.frequency_plot):
            target.log_scale = text == "Log"
            target.update()

    def dragEnterEvent(self, event) -> None:
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self.load_paths(paths)
            event.acceptProposedAction()

