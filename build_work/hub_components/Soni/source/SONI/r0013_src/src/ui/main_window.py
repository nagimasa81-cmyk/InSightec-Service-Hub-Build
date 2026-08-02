from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSettings, Qt, QTimer, QSize, QRectF, QEvent
from PySide6.QtGui import QAction, QImage, QPixmap, QIcon, QCursor, QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QGroupBox, QHeaderView,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QSlider, QSpinBox, QDoubleSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget, QDialog, QGridLayout, QToolButton, QMenu, QFormLayout,
)

from src.common.constants import APP_NAME, APP_VERSION, ORGANIZATION
from src.domain.models import SonicationModel
from src.integration.spectrum_provider import SpectrumMsgAnalyzerAdapter
from src.services.discovery_service import DiscoveryService
from src.services.import_service import ImportService
from src.services.replay_service import ReplayService
from src.services.acoustic_control_service import AcousticControlService
from src.services.sonication_channel_service import SonicationChannelService
from src.services.sonication_metadata_service import SonicationMetadataService
from src.services.skull_measures_service import SkullMeasuresService
from src.services.hydrophone_replay_service import HydrophoneReplayService
from src.services.hydrophone_calibration_service import HydrophoneCalibrationService
from src.integration.spectrum_provider import SpectrumFrame
from src.core.chart_state import ChartState
from src.core.replay_context import ReplayContext, ReplaySelection
from src.core.replay_snapshot import ReplayFrameSnapshot, ReplaySnapshotProvider
from src.ui.replay_view_coordinator import ReplayViewCoordinator
from src.core.relative_spectrum_renderer import RelativeSpectrumRenderer
from src.core.current_spectrum_renderer import CurrentSpectrumRenderer
from src.ui.image_panel import OverlayPanel
from src.ui.diagnostics import DiagnosticsTab
from src.ui.hydrophone_window import EightHydrophoneWindow

LOG = logging.getLogger(__name__)


class InfoWindow(QDialog):
    """Non-modal, movable, minimizable information window kept above the replay UI."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sonication Information")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)
        self.resize(540, 360)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Item", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    def update_rows(self, rows):
        self.table.setRowCount(len(rows))
        for r, (key, value) in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(key)))
            self.table.setItem(r, 1, QTableWidgetItem(str(value)))


class DetailWindow(InfoWindow):
    """Reusable single-instance non-modal detail table."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(620, 430)


class TransducerMapWidget(QWidget):
    """Workstation-style transducer element map. This is deliberately not a chart."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(650, 520)
        self.data = None
        self.parameter = "Element SDR"
        self.show_enabled = True
        self.show_disabled = True
        self._screen_points = []
        self.setMouseTracking(True)
        self.tooltip = ""
        self.display_max = None
        self.display_min = None
        self.scale_mode = "Adaptive"
        self.gamma = 1.0
        self._lut = [self._interpolate_lut(i / 255.0) for i in range(256)]

    def configure(self, data, parameter, show_enabled, show_disabled, display_min=None, display_max=None, scale_mode="Adaptive", gamma=1.0):
        self.data = data
        self.parameter = parameter
        self.show_enabled = show_enabled
        self.show_disabled = show_disabled
        self.display_min = float(display_min) if display_min is not None else None
        self.display_max = float(display_max) if display_max is not None else None
        self.scale_mode = str(scale_mode or "Adaptive")
        self.gamma = max(0.25, min(4.0, float(gamma)))
        self.update()

    @staticmethod
    def _interpolate_lut(level):
        """Workstation-like SDR LUT: deep blue → cyan → green → yellow → red → magenta."""
        level = max(0.0, min(1.0, float(level)))
        stops = [
            (0.00, (20, 38, 170)),
            (0.16, (20, 82, 222)),
            (0.34, (18, 190, 220)),
            (0.52, (40, 205, 102)),
            (0.68, (205, 220, 42)),
            (0.82, (250, 170, 28)),
            (0.94, (238, 58, 38)),
            (0.985, (232, 40, 120)),
            (1.00, (235, 35, 175)),
        ]
        for (x0,c0),(x1,c1) in zip(stops,stops[1:]):
            if level <= x1:
                t=(level-x0)/(x1-x0) if x1>x0 else 0.0
                return QColor(*[round(a+(b-a)*t) for a,b in zip(c0,c1)])
        return QColor(*stops[-1][1])

    def _color(self, level):
        index = max(0, min(255, int(round(float(level) * 255.0))))
        return self._lut[index]

    def _display_color(self, normalized_level):
        """Return the exact colour used by both elements and the legend.

        Keeping gamma and LUT lookup in one function prevents the element map
        and colour bar from drifting apart when display settings change.
        """
        level = min(1.0, max(0.0, float(normalized_level)))
        return self._color(level ** self.gamma)

    def _draw_color_bar(self, painter, bar, lo, hi):
        """Draw a true scan-line gradient from the shared display LUT.

        A one-pixel-wide QImage stretched by QPainter was rendered as a nearly
        solid colour on some Windows/Qt raster backends.  Drawing every screen
        row explicitly avoids that backend-specific scaling path and guarantees
        that the legend matches the element colours exactly.
        """
        top = int(round(bar.top()))
        bottom = int(round(bar.bottom()))
        left = int(round(bar.left()))
        right = int(round(bar.right()))
        height = max(1, bottom - top)
        for y in range(top, bottom + 1):
            normalized = 1.0 - ((y - top) / height)
            painter.setPen(QPen(self._display_color(normalized), 1.0))
            painter.drawLine(left, y, right, y)

        painter.setPen(QPen(QColor(70, 70, 68), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(bar)
        painter.setPen(QColor(45, 45, 43))
        for i in range(11):
            normalized = i / 10.0
            y = bar.bottom() - normalized * bar.height()
            value = lo + normalized * (hi - lo)
            painter.drawLine(int(bar.right()), int(y), int(bar.right() + 5), int(y))
            painter.drawText(
                QRectF(bar.right() + 8, y - 9, 48, 18),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                f"{value:.2f}",
            )

    @staticmethod
    def _robust_limits(values, requested_lo, requested_hi, mode):
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        if finite.size == 0:
            return 0.0, 1.0
        mode = str(mode or "Adaptive")
        if mode == "Manual":
            lo = float(requested_lo) if requested_lo is not None else float(np.min(finite))
            hi = float(requested_hi) if requested_hi is not None else float(np.max(finite))
        elif mode == "Normalized":
            lo, hi = float(np.percentile(finite, 2.0)), float(np.percentile(finite, 98.0))
        else:  # Adaptive: preserve physical values but suppress isolated extremes.
            lo, hi = float(np.percentile(finite, 1.0)), float(np.percentile(finite, 99.0))
        if not np.isfinite(lo): lo = float(np.min(finite))
        if not np.isfinite(hi): hi = float(np.max(finite))
        if hi <= lo:
            hi = lo + max(abs(lo) * 1e-6, 1e-6)
        return lo, hi

    @staticmethod
    def _ring_radii(xs, ys, cx, cy):
        radii = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        if radii.size < 8:
            return []
        ordered = np.sort(radii)
        gaps = np.diff(ordered)
        threshold = max(float(np.median(gaps) * 5.0), float((ordered[-1] - ordered[0]) / 80.0))
        split = np.where(gaps > threshold)[0] + 1
        groups = np.split(ordered, split)
        centers = [float(np.median(g)) for g in groups if len(g) >= 3]
        # Avoid drawing every element row as a ring; retain the major radial bands only.
        if len(centers) > 8:
            idx = np.linspace(0, len(centers) - 1, 6).round().astype(int)
            centers = [centers[i] for i in sorted(set(idx.tolist()))]
        return centers

    @staticmethod
    def _sector_angles(xs, ys, cx, cy):
        angles = np.mod(np.arctan2(ys - cy, xs - cx), 2 * np.pi)
        if angles.size < 12:
            return []
        ordered = np.sort(angles)
        wrapped = np.concatenate([ordered, [ordered[0] + 2 * np.pi]])
        gaps = np.diff(wrapped)
        # The six physical sector gaps are the largest angular gaps in the actual cloud.
        count = min(6, len(gaps))
        candidates = np.argsort(gaps)[-count:]
        return sorted(float((wrapped[i] + gaps[i] / 2.0) % (2 * np.pi)) for i in candidates)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # The treatment workstation uses a neutral light canvas around the element field.
        painter.fillRect(self.rect(), QColor(226, 226, 224))
        self._screen_points = []
        if not self.data or not self.data.elements:
            painter.setPen(QColor(45, 45, 45))
            msg = self.data.error if self.data and self.data.error else "No SkullMeasures data"
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, msg)
            return

        rows = []
        for el in self.data.elements:
            if el.enabled and not self.show_enabled:
                continue
            if not el.enabled and not self.show_disabled:
                continue
            x = el.values.get("Element X", float("nan"))
            y = el.values.get("Element Y", float("nan"))
            value = el.values.get(self.parameter, float("nan"))
            if np.isfinite(x) and np.isfinite(y):
                rows.append((el, float(x), float(y), float(value)))
        if not rows:
            painter.setPen(QColor(45, 45, 45))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No elements match the display filters")
            return

        vals = np.asarray([r[3] for r in rows if np.isfinite(r[3])], float)
        lo, hi = self._robust_limits(vals, self.display_min, self.display_max, self.scale_mode)
        if self.parameter == "Element SDR" and self.scale_mode != "Manual":
            lo, hi = 0.0, 1.0

        # Reserve a compact lower-right strip for the vertical colour legend.
        map_rect = QRectF(26, 18, max(120, self.width() - 150), max(120, self.height() - 42))
        xs = np.asarray([r[1] for r in rows], float)
        ys = np.asarray([r[2] for r in rows], float)
        xmin, xmax = float(xs.min()), float(xs.max())
        ymin, ymax = float(ys.min()), float(ys.max())
        span = max(xmax - xmin, ymax - ymin, 1.0)
        scale = min(map_rect.width(), map_rect.height()) / span * 0.94
        cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
        sx, sy = map_rect.center().x(), map_rect.center().y()

        # Estimate element pitch from the real coordinate cloud, then size the markers
        # to match the dense dot field of the treatment workstation.
        nearest = []
        if len(rows) > 1:
            sample = np.column_stack((xs, ys))
            stride = max(1, len(sample) // 180)
            for pt in sample[::stride]:
                d2 = np.sum((sample - pt) ** 2, axis=1)
                d2[d2 == 0] = np.inf
                nearest.append(float(np.sqrt(np.min(d2))))
        pitch = float(np.median(nearest)) if nearest else span / 40.0
        radius = max(1.8, min(4.4, pitch * scale * 0.31))

        # Geometry-derived guides: use the real radial bands and physical sector gaps.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(178, 178, 174), 0.65))
        ring_radii = self._ring_radii(xs, ys, cx, cy)
        for physical_radius in ring_radii:
            rr = physical_radius * scale
            painter.drawEllipse(map_rect.center(), rr, rr)
        outer_physical = float(np.max(np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)))
        outer = outer_physical * scale
        painter.setPen(QPen(QColor(190, 190, 186), 0.55))
        for angle in self._sector_angles(xs, ys, cx, cy):
            x2 = sx + np.cos(angle) * outer
            y2 = sy - np.sin(angle) * outer
            painter.drawLine(int(sx), int(sy), int(x2), int(y2))

        finite_rows = [r for r in rows if np.isfinite(r[3]) and r[0].enabled]
        max_element = max(finite_rows, key=lambda r: r[3]) if finite_rows else None
        for el, x, y, value in rows:
            px = sx + (x - cx) * scale
            py = sy - (y - cy) * scale
            radial_fraction = min(1.0, max(0.0, np.hypot(x - cx, y - cy) / max(outer_physical, 1e-9)))
            point_radius = radius * (1.12 - 0.24 * radial_fraction)
            if el.enabled:
                level = (value - lo) / (hi - lo) if np.isfinite(value) else 0.0
                level = min(1.0, max(0.0, level))
                color = self._display_color(level)
            else:
                color = QColor(145, 145, 142)
            painter.setPen(QPen(QColor(95, 95, 92), 0.30))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QRectF(px - point_radius, py - point_radius, 2 * point_radius, 2 * point_radius))
            self._screen_points.append((px, py, point_radius, el, value))

            # Workstation-like hot-element locator: a compact magenta square over max SDR.
            if max_element is not None and el.number == max_element[0].number:
                painter.setPen(QPen(QColor(245, 210, 235), 0.9))
                painter.setBrush(QBrush(QColor(236, 22, 166)))
                side = max(4.0, radius * 1.55)
                painter.drawRect(QRectF(px - side / 2, py - side / 2, side, side))

        # Vertical workstation-style colour scale.
        bar_h = min(260.0, max(150.0, self.height() * 0.46))
        bar = QRectF(self.width() - 77, self.height() - bar_h - 48, 22, bar_h)
        self._draw_color_bar(painter, bar, lo, hi)

        # Small selector/value boxes mimic the reference console without pretending to
        # reproduce proprietary controls.
        badge = QRectF(bar.left() - 3, bar.top() - 34, bar.width() + 8, 25)
        painter.setPen(QPen(QColor(95, 95, 90), 1.0))
        painter.setBrush(QBrush(QColor(245, 230, 205)))
        painter.drawRect(badge)
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "1")
        zero_badge = QRectF(bar.left() - 3, bar.bottom() + 8, bar.width() + 8, 25)
        painter.drawRect(zero_badge)
        painter.drawText(zero_badge, Qt.AlignmentFlag.AlignCenter, f"{lo:.0f}")

        painter.setPen(QColor(45, 45, 43))
        painter.drawText(QRectF(8, 8, 190, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self.parameter)
    def mouseMoveEvent(self, event):
        x,y=event.position().x(),event.position().y()
        hit=None
        for px,py,r,el,value in self._screen_points:
            if (px-x)**2+(py-y)**2 <= (r+4)**2:
                hit=(el,value); break
        if hit:
            el,value=hit
            self.setToolTip(f"Element {el.number}\n{self.parameter}: {value:.5g}\nEnabled: {'Yes' if el.enabled else 'No'}\nFailure reason: {el.failure_reason}")
        else:
            self.setToolTip("")
        super().mouseMoveEvent(event)


class XDWindow(QDialog):
    """SkullMeasures transducer element map with automatic parameter updates."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XD - Skull Element Map — RC2-R0015")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setModal(False)
        self.resize(920, 720)
        self.data = None
        self.parameter = QComboBox()
        self.parameter.addItems(list(SkullMeasuresService.PARAMETERS.keys()))
        self.parameter.setCurrentText("Element SDR")
        self.show_enabled = QCheckBox("Enable Elements"); self.show_enabled.setChecked(True)
        self.show_disabled = QCheckBox("Disable Elements"); self.show_disabled.setChecked(True)
        self.scale_mode = QComboBox(); self.scale_mode.addItems(["Adaptive", "Manual", "Normalized"]); self.scale_mode.setCurrentText("Adaptive")
        self.gamma = QDoubleSpinBox(); self.gamma.setDecimals(2); self.gamma.setRange(0.25, 4.0); self.gamma.setSingleStep(0.05); self.gamma.setValue(1.15); self.gamma.setKeyboardTracking(False)
        self.scale_min = QDoubleSpinBox(); self.scale_min.setDecimals(3); self.scale_min.setRange(-999999.0,999999.0); self.scale_min.setKeyboardTracking(False)
        self.scale_max = QDoubleSpinBox()
        self.scale_max.setDecimals(3); self.scale_max.setRange(0.001, 999999.0); self.scale_max.setValue(1.0)
        self.scale_max.setKeyboardTracking(False); self.scale_max.setToolTip("Upper value of the colour scale")
        self.source_label = QLabel("No SkullMeasures data")
        self.source_label.setWordWrap(True)
        self.summary_label = QLabel("Elements: -")
        self.map = TransducerMapWidget(self)
        self.parameter.currentTextChanged.connect(self._redraw)
        self.show_enabled.toggled.connect(self._redraw)
        self.show_disabled.toggled.connect(self._redraw)
        self.scale_mode.currentTextChanged.connect(self._redraw)
        self.gamma.valueChanged.connect(self._redraw)
        self.scale_min.valueChanged.connect(self._redraw)
        self.scale_max.valueChanged.connect(self._redraw)
        controls=QHBoxLayout()
        controls.addWidget(QLabel("Parameter")); controls.addWidget(self.parameter,1)
        controls.addWidget(QLabel("Scale")); controls.addWidget(self.scale_mode)
        controls.addWidget(QLabel("Min")); controls.addWidget(self.scale_min)
        controls.addWidget(QLabel("Max")); controls.addWidget(self.scale_max)
        controls.addWidget(QLabel("Gamma")); controls.addWidget(self.gamma)
        controls.addWidget(self.show_enabled); controls.addWidget(self.show_disabled)
        layout=QVBoxLayout(self)
        layout.addLayout(controls); layout.addWidget(self.source_label)
        layout.addWidget(self.map,1); layout.addWidget(self.summary_label)

    def set_data(self, data):
        self.data=data
        if data and data.source:
            self.source_label.setText(f"Source: {data.source.name}")
        else:
            self.source_label.setText(data.error if data else "SkullMeasures log not found")
        if data and data.elements:
            values=[el.values.get(self.parameter.currentText(), float("nan")) for el in data.elements]
            values=np.asarray(values,float); values=values[np.isfinite(values)]
            if values.size:
                self.scale_min.blockSignals(True); self.scale_min.setValue(float(np.nanmin(values))); self.scale_min.blockSignals(False)
                self.scale_max.blockSignals(True); self.scale_max.setValue(float(np.nanmax(values))); self.scale_max.blockSignals(False)
        self._redraw()

    def _redraw(self, *_):
        self.map.configure(self.data,self.parameter.currentText(),self.show_enabled.isChecked(),self.show_disabled.isChecked(),self.scale_min.value(),self.scale_max.value(),self.scale_mode.currentText(),self.gamma.value())
        if not self.data or not self.data.elements:
            self.summary_label.setText("Elements: 0")
            return
        enabled=sum(1 for e in self.data.elements if e.enabled)
        vals=[e.values.get(self.parameter.currentText(),float("nan")) for e in self.data.elements]
        finite=np.asarray([v for v in vals if np.isfinite(v)],float)
        value_text=f"{float(np.min(finite)):.4g} to {float(np.max(finite)):.4g}" if finite.size else "Unavailable"
        self.summary_label.setText(f"{self.parameter.currentText()}: {value_text}    Scale: {self.scale_mode.currentText()}    Gamma: {self.gamma.value():.2f}    Elements: {len(self.data.elements)}    On: {enabled}    Off: {len(self.data.elements)-enabled}")


class HoldInfoButton(QPushButton):
    """Shows a temporary popup only while the right mouse button is held."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.popup = QLabel()
        self.popup.setWindowFlags(Qt.WindowType.ToolTip)
        self.popup.setStyleSheet("QLabel { background:#152536; color:white; border:1px solid #4c789d; padding:10px; }")

    def set_popup_text(self, text):
        self.popup.setText(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.popup.adjustSize()
            self.popup.move(QCursor.pos())
            self.popup.show()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.popup.hide()
            event.accept()
            return
        super().mouseReleaseEvent(event)



class ChartPopup(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowCloseButtonHint)
        self.setModal(False); self.resize(1000,650)
        self.plot = pg.PlotWidget(title=title); self.plot.showGrid(x=True,y=True,alpha=.2)
        self.hover_series = []
        self.hover_text = pg.TextItem(anchor=(0, 1), color="#ffffff", fill=pg.mkBrush(0, 0, 0, 210))
        self.hover_text.setZValue(100); self.hover_text.hide(); self.plot.addItem(self.hover_text)
        self.hover_proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=45, slot=self._hovered)
        layout=QVBoxLayout(self); layout.addWidget(self.plot)

    def set_hover_series(self, series):
        """series: [(label, x-array, y-array, unit), ...]."""
        self.hover_series = series or []
        if not self.hover_series:
            self.hover_text.hide()

    def _hovered(self, event):
        scene_pos = event[0] if isinstance(event, (tuple, list)) else event
        if not self.hover_series or not self.plot.sceneBoundingRect().contains(scene_pos):
            self.hover_text.hide(); return
        point = self.plot.plotItem.vb.mapSceneToView(scene_pos)
        lines=[]; best_x=None
        for label, x_values, y_values, unit in self.hover_series:
            x=np.asarray(x_values,float); y=np.asarray(y_values,float)
            valid=np.isfinite(x)&np.isfinite(y)
            if not valid.any(): continue
            xv=x[valid]; yv=y[valid]; i=int(np.argmin(np.abs(xv-point.x())))
            if best_x is None: best_x=float(xv[i]); lines.append(f"{best_x:.2f} sec")
            lines.append(f"{label}: {float(yv[i]):.2f}{unit}")
        if not lines:
            self.hover_text.hide(); return
        self.hover_text.setText("\n".join(lines)); self.hover_text.setPos(point.x(),point.y()); self.hover_text.show()


class MainWindow(QMainWindow):
    """FUS workstation-inspired Sonication-folder replay UI.

    The RC1 replay UI deliberately prioritizes replay-first behavior. The
    partially developed acoustic-analysis controls remain available on the
    Analysis tab, but they no longer reduce the size of the replay image.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.resize(1760, 1040)
        self.setMinimumSize(1180, 720)
        self.setAcceptDrops(True)

        self.settings = QSettings(ORGANIZATION, APP_NAME)
        self.importer = ImportService()
        self.discovery = DiscoveryService()
        self.replay = ReplayService()
        self.acoustic_control_service = AcousticControlService()
        self.package = None
        self.current: SonicationModel | None = None
        self.frame_index = 0
        # Runtime render diagnostics.  These counters deliberately live in the
        # real GUI path (not only tests) so packaged EXEs can prove that a click
        # or arrow reached the image renderer.
        self._render_serial = 0
        self._last_render_signature = None
        self.replay_context = ReplayContext(self)
        self.replay_views = ReplayViewCoordinator(self.replay_context)
        self.snapshot_provider = ReplaySnapshotProvider(
            self.replay.frame, self._index_to_seconds, self._map_replay_to_data
        )
        # R0010: RC1 direct rendering is the authoritative runtime path.
        # Do not register the removed RC2 callback; doing so caused the packaged
        # EXE to fail in MainWindow.__init__ before the window could appear.
        self.max_temperature_trend: list[float] = []
        self.mean_temperature_trend: list[float] = []
        self.delta_trend: list[float] = []
        self.temperature_display_mode = "Absolute Temperature"
        self.spectrum_channels: dict[str, list] = {}
        self.chart_state = ChartState()
        self.cpc_enabled = self.chart_state.cpc_enabled
        self.sonication_channel_service = SonicationChannelService()
        self.metadata_service = SonicationMetadataService()
        self.skull_measures_service = SkullMeasuresService()
        self.hydrophone_replay_service = HydrophoneReplayService()
        self.hydrophone_calibration_service = HydrophoneCalibrationService()
        self.hydrophone_calibration = None
        self.hydrophone_window = None
        self.current_metadata = None
        self.relative_spectrum_renderer = RelativeSpectrumRenderer()
        self.current_spectrum_renderer = CurrentSpectrumRenderer()
        self._active_spectrum_channel = "CH0"
        self._channel_colors = {
            "CH0":"#ff3b30", "CH1":"#ff9500", "CH2":"#ffd60a", "CH3":"#9ef01a",
            "CH4":"#30d158", "CH5":"#32d7ff", "CH6":"#0a84ff", "CH7":"#bf5af2",
        }
        self.spectrum_provider = SpectrumMsgAnalyzerAdapter()
        self._spectrum_frame = None
        self._spectrum_status = "No SpectrumMsg"
        self.sonication_index = -1
        self.cursor_temperature_trend: list[float] = []
        self._overlay_session_view = None
        self._overlay_session_levels = None
        self._restore_overlay_session = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        # R0014: vendor-workstation replay behavior.  In this mode the charts
        # reveal only acquired data, the thumbnail rows follow the live frame,
        # and playback stops at the end instead of wrapping silently.
        self.workstation_replay_enabled = True
        self._workstation_phase = "Ready"

        pg.setConfigOption("background", "k")
        pg.setConfigOption("foreground", "w")

        self._build_actions()
        self._build_ui()
        self._restore()

    # ------------------------------------------------------------------ UI
    def _build_actions(self):
        menu = self.menuBar().addMenu("&File")
        open_zip = QAction("Open ZIP...", self)
        open_zip.triggered.connect(self.open_zip)
        menu.addAction(open_zip)
        open_folder = QAction("Open Folder...", self)
        open_folder.triggered.connect(self.open_folder)
        menu.addAction(open_folder)

        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(False)
        toolbar.addAction(open_zip)
        toolbar.addAction(open_folder)
        toolbar.addSeparator()
        self.open_hydrophone_action = QAction("Open 8CH Hydrophone", self)
        self.open_hydrophone_action.setToolTip("Open independent CPCFiles 8-channel analyzer")
        self.open_hydrophone_action.triggered.connect(self._open_hydrophone_window)
        toolbar.addAction(self.open_hydrophone_action)

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_replay_tab(), "Replay")
        self.tabs.addTab(self._build_analysis_tab(), "Analysis (preserved)")
        self.tabs.addTab(self._build_planning_tab(), "Planning / Reference")
        self.diagnostics_tab = DiagnosticsTab(self)
        self.diagnostics_tab.sonicationRequested.connect(self._select_sonication_index)
        self.tabs.addTab(self.diagnostics_tab, "Diagnostics")
        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("Ready")

    def _chart_panel(self, title: str, plot: pg.PlotWidget, key: str) -> QWidget:
        panel=QGroupBox(title); lay=QVBoxLayout(panel); lay.setContentsMargins(3,3,3,3); lay.setSpacing(1)
        header=QHBoxLayout(); header.setContentsMargins(0,0,0,0)
        expand=QToolButton(); expand.setText("↗"); expand.setToolTip("Open enlarged chart")
        expand.setFixedSize(20,20); expand.setStyleSheet("QToolButton{padding:0;font-size:10px;}")
        expand.clicked.connect(lambda: self._open_chart_popup(key))
        header.addStretch(1); header.addWidget(expand); lay.addLayout(header); lay.addWidget(plot,1)
        return panel

    def _make_image_strip(self, role: str) -> QListWidget:
        widget = QListWidget()
        widget.setProperty("imageRole", role)
        widget.setViewMode(QListWidget.ViewMode.IconMode)
        widget.setIconSize(QSize(88, 70)); widget.setGridSize(QSize(98, 88))
        widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        widget.setMovement(QListWidget.Movement.Static)
        widget.setFlow(QListWidget.Flow.LeftToRight)
        widget.setWrapping(False)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setMaximumHeight(92); widget.setMinimumHeight(86)
        return widget

    def _clear_replay_display(self) -> None:
        """Remove every visual belonging to the previous sonication."""
        self.timer.stop()
        if hasattr(self, "play_btn"): self.play_btn.setText("▶")
        if hasattr(self, "overlay"):
            self.overlay.set_hover_temperature(None)
            self.overlay.set_roi(None, None)
            self.overlay.set_overlay(None, None, fit=False)
        for name in ("planning_frame_list", "anatomy_frame_list", "thermal_frame_list"):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.blockSignals(True); widget.clear(); widget.blockSignals(False)
        for curve_name in ("max_temperature_curve", "mean_temperature_curve", "cursor_temperature_curve", "acoustic_power_curve", "acoustic_score_curve"):
            curve = getattr(self, curve_name, None)
            if curve is not None:
                try: curve.setData([], [])
                except Exception: pass
        if hasattr(self, "spectrum_plot"): self.spectrum_plot.clear()
        if hasattr(self, "frame_label"): self.frame_label.setText("Frame -/-")
        if hasattr(self, "sync_label"): self.sync_label.setText("Loading selected sonication...")
        self._planning_display_arrays = []
        self._planning_assets_all = []
        self._anatomy_row_map = []
        self._thermal_row_map = []
        self._main_image_mode = "thermal"

    @staticmethod
    def _decode_planning_image(asset):
        """Decode a planning image with CtImage metadata; never guess CT dtype."""
        path = Path(asset.path)
        try:
            suffix = path.suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
                image = QImage(str(path))
                if image.isNull(): return None
                image = image.convertToFormat(QImage.Format.Format_Grayscale8)
                ptr = image.bits(); arr = np.frombuffer(ptr, np.uint8, image.width()*image.height())
                return arr.reshape(image.height(), image.width()).astype(np.float32)
            if suffix != ".raw": return None
            width = getattr(asset, "width", None); height = getattr(asset, "height", None)
            dtype_name = getattr(asset, "dtype", None)
            if width and height and dtype_name:
                dtype = np.dtype(dtype_name)
                expected = int(width) * int(height) * dtype.itemsize
                if path.stat().st_size != expected:
                    return None
                values = np.fromfile(path, dtype=dtype).reshape(int(height), int(width)).astype(np.float32)
                finite = values[np.isfinite(values)]
                return values if finite.size and float(np.nanstd(finite)) > 1e-8 else None
            # Non-CT planning MR fallback remains conservative.
            size = path.stat().st_size
            for dtype in (np.dtype('<u2'), np.dtype('<i2'), np.dtype('<f4')):
                count = size // dtype.itemsize; side = int(round(count ** 0.5))
                if side >= 32 and side * side == count:
                    values = np.fromfile(path, dtype=dtype).reshape(side, side).astype(np.float32)
                    finite = values[np.isfinite(values)]
                    if finite.size and float(np.nanstd(finite)) > 1e-8:
                        return values
            return None
        except (OSError, ValueError, TypeError):
            return None

    def _planning_type_changed(self, _text: str) -> None:
        self._rebuild_planning_strip()

    def _planning_category(self, asset) -> str:
        text = " ".join(str(getattr(asset, name, "")) for name in ("category", "role", "path")).lower()
        if "ct" in text or "skull" in text:
            return "Planning CT"
        if "mr" in text or "mri" in text or "dicom" in text:
            return "Planning MR"
        return "Planning Other"

    def _rebuild_planning_strip(self) -> None:
        if not hasattr(self, "planning_frame_list"):
            return
        selected = self.planning_type_combo.currentText() if hasattr(self, "planning_type_combo") else "All Planning"
        self.planning_frame_list.blockSignals(True); self.planning_frame_list.clear()
        self._planning_display_arrays = []
        for asset, array, label, category in getattr(self, "_planning_assets_all", []):
            if selected not in ("", "All Planning") and category != selected:
                continue
            icon = self._array_icon(array) if array is not None else QIcon()
            item = QListWidgetItem(icon, label); item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setToolTip(f"{getattr(asset, 'role', category)}\n{getattr(asset, 'path', '')}")
            self.planning_frame_list.addItem(item)
            self._planning_display_arrays.append((array, label))
        self.planning_frame_list.blockSignals(False)

    def _first_valid_replay_frame(self) -> int:
        """Return the first frame that can actually render an anatomy image."""
        if not self.current:
            return 0
        count = max(1, int(self.current.replay_frame_count))
        for index in range(count):
            try:
                data = self.replay.frame(self.current, index)
                magnitude = getattr(data, "magnitude", None)
                if magnitude is not None:
                    arr = np.asarray(magnitude, float)
                    finite = arr[np.isfinite(arr)]
                    if finite.size and float(np.nanstd(finite)) > 1e-8:
                        return index
            except Exception:
                continue
        return 0

    def _planning_frame_selected(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "_planning_display_arrays", [])): return
        array, label = self._planning_display_arrays[row]
        if array is None:
            self.statusBar().showMessage(f"Planning resource is metadata only: {label}")
            return
        self._main_image_mode = "planning"
        self.overlay.set_hover_temperature(None); self.overlay.set_roi(None, None)
        self.overlay.set_overlay(array, None, fit=True)
        self.frame_label.setText(f"Planning image: {label}")
        self.sync_label.setText("Planning CT / MR selected")

    def _anatomy_frame_selected(self, row: int) -> None:
        if not self.current or row < 0 or not self.current.magnitude_frames: return
        source_row = self._anatomy_row_map[row] if row < len(self._anatomy_row_map) else row
        replay_index = self._map_replay_to_data(source_row, len(self.current.magnitude_frames), self.current.replay_frame_count)
        self._main_image_mode = "anatomy"
        self.set_frame(replay_index, display_mode="anatomy")

    def _thermal_frame_selected(self, row: int) -> None:
        if not self.current or row < 0: return
        source_row = self._thermal_row_map[row] if row < len(self._thermal_row_map) else row
        series_count = max(1, len(self.current.temperature_frames))
        replay_index = self._map_replay_to_data(source_row, series_count, self.current.replay_frame_count)
        self._main_image_mode = "thermal"
        self.set_frame(replay_index, display_mode="thermal")

    def _build_replay_tab(self) -> QWidget:
        # Compact top strip: Sonication number is intentionally not a list.
        self.son_prev_btn = QPushButton("≪")
        self.son_next_btn = QPushButton("≫")
        self.son_number_btn = HoldInfoButton("-")
        self.son_number_btn.setMinimumWidth(64)
        self.son_prev_btn.clicked.connect(lambda: self._change_sonication(-1))
        self.son_next_btn.clicked.connect(lambda: self._change_sonication(1))
        self.info_btn = QPushButton("Info")
        self.mr_btn = QPushButton("MR")
        self.scan_btn = QPushButton("Scan")
        self.xd_btn = QPushButton("XD")
        self.info_btn.clicked.connect(self._show_info_window)
        self.mr_btn.clicked.connect(self._show_mr_window)
        self.scan_btn.clicked.connect(self._show_scan_window)
        self.xd_btn.clicked.connect(self._show_xd_window)
        self.info_window = InfoWindow(self)
        self.mr_window = DetailWindow("MR Information", self)
        self.scan_window = DetailWindow("Scan Protocol Information", self)
        self.xd_window = XDWindow(self)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Sonication No."))
        top_bar.addWidget(self.son_prev_btn)
        top_bar.addWidget(self.son_number_btn)
        top_bar.addWidget(self.son_next_btn)
        top_bar.addWidget(QLabel("Right-click and hold for details"))
        top_bar.addStretch(1)

        # Left controls: temperature scale and a true slider for red threshold.
        self.temperature_mode_combo = QComboBox()
        self.temperature_mode_combo.addItems(["Absolute Temperature", "ΔTemperature (Investigation)"])
        self.temperature_mode_combo.currentTextChanged.connect(self._temperature_mode_changed)
        self.range_combo = QComboBox()
        self.range_combo.addItems(["40–60 °C", "35–60 °C", "30–90 °C", "0–60 °C", "Auto"])
        self.range_combo.currentIndexChanged.connect(self._temperature_range_changed)
        self.overlay_opacity = QSlider(Qt.Orientation.Horizontal)
        self.overlay_opacity.setRange(0, 100); self.overlay_opacity.setValue(55)
        self.overlay_opacity.valueChanged.connect(lambda _: self.set_frame(self.frame_index))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(30, 90); self.threshold_slider.setValue(48)
        self.threshold_minus = QPushButton("◀"); self.threshold_plus = QPushButton("▶")
        for button in (self.threshold_minus, self.threshold_plus): button.setFixedWidth(28)
        self.threshold_minus.clicked.connect(lambda: self.threshold_slider.setValue(self.threshold_slider.value()-1))
        self.threshold_plus.clicked.connect(lambda: self.threshold_slider.setValue(self.threshold_slider.value()+1))
        self.threshold_value = QLabel("Red starts at 48 °C")
        self.threshold_slider.valueChanged.connect(self._threshold_changed)
        self.baseline_label = QLabel("Temperature source: waiting")
        self.baseline_label.setWordWrap(True); self.baseline_label.setObjectName("CurrentValue")
        self.cursor_temperature_label = QLabel("Cursor Temperature: --")
        self.cursor_temperature_label.setWordWrap(True); self.cursor_temperature_label.setObjectName("CurrentValue")

        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(3,3,3,3)
        ll.addWidget(QLabel("Temperature display")); ll.addWidget(self.temperature_mode_combo)
        ll.addWidget(QLabel("Overlay opacity")); ll.addWidget(self.overlay_opacity)
        ll.addWidget(QLabel("Temperature range")); ll.addWidget(self.range_combo)
        ll.addWidget(QLabel("Red Threshold"));
        threshold_row=QHBoxLayout(); threshold_row.setContentsMargins(0,0,0,0); threshold_row.setSpacing(3)
        threshold_row.addWidget(self.threshold_minus); threshold_row.addWidget(self.threshold_slider,1); threshold_row.addWidget(self.threshold_plus)
        ll.addLayout(threshold_row); ll.addWidget(self.threshold_value)
        self.voxel_label = QLabel("Voxel (ROI)  3 pixels × 3 pixels"); self.voxel_label.setObjectName("CurrentValue"); ll.addWidget(self.voxel_label)
        ll.addWidget(self.cursor_temperature_label)
        ll.addWidget(self.baseline_label); ll.addStretch(1)
        self.sonication_summary_box = QGroupBox("Sonication")
        summary_layout = QFormLayout(self.sonication_summary_box); summary_layout.setContentsMargins(5,8,5,5); summary_layout.setSpacing(2)
        self.summary_value_labels = {}
        for key in ("Orientation", "Frequency Dir", "Energy", "Power", "Duration", "Frequency"):
            value_label=QLabel("-"); value_label.setObjectName("CurrentValue"); value_label.setWordWrap(True)
            self.summary_value_labels[key]=value_label; summary_layout.addRow(key, value_label)
        ll.addWidget(self.sonication_summary_box)
        info_buttons=QHBoxLayout(); info_buttons.setSpacing(2)
        for button in (self.info_btn,self.mr_btn,self.scan_btn,self.xd_btn):
            button.setMinimumWidth(32); info_buttons.addWidget(button)
        ll.addLayout(info_buttons)
        left.setMinimumWidth(190); left.setMaximumWidth(245)

        # Dominant workstation image. Click moves the crosshair and updates temperature.
        self.overlay = OverlayPanel("Thermal Replay - Workstation Temperature Map")
        self.overlay.cursorMoved.connect(self._overlay_cursor_moved)
        self.overlay.viewStateChanged.connect(self._capture_overlay_state_debounced)
        self.overlay.levelsChanged.connect(self._capture_overlay_levels)
        self._overlay_save_timer=QTimer(self); self._overlay_save_timer.setSingleShot(True); self._overlay_save_timer.timeout.connect(self._save_overlay_state)
        self._fit_overlay_next = True
        self.cursor_x = None; self.cursor_y = None

        # Product-style three independent image rows.  Each row scrolls
        # horizontally and selects what is shown in the main image viewer.
        self.planning_frame_list = self._make_image_strip("planning")
        self.anatomy_frame_list = self._make_image_strip("anatomy")
        self.thermal_frame_list = self._make_image_strip("thermal")
        self.planning_type_combo = QComboBox()
        self.planning_type_combo.setMinimumWidth(135)
        image_row_options = ["Planning CT", "Planning MR", "Anatomy MR", "Thermal", "All images"]
        self.planning_type_combo.addItems(image_row_options)
        self.anatomy_type_combo = QComboBox(); self.anatomy_type_combo.addItems(image_row_options)
        self.thermal_type_combo = QComboBox(); self.thermal_type_combo.addItems(image_row_options)
        self.planning_type_combo.setCurrentText("Planning CT")
        self.anatomy_type_combo.setCurrentText("Anatomy MR")
        self.thermal_type_combo.setCurrentText("Thermal")
        for combo in (self.planning_type_combo,self.anatomy_type_combo,self.thermal_type_combo): combo.setMinimumWidth(135)
        self.planning_type_combo.currentTextChanged.connect(self._rebuild_all_image_strips)
        self.anatomy_type_combo.currentTextChanged.connect(self._rebuild_all_image_strips)
        self.thermal_type_combo.currentTextChanged.connect(self._rebuild_all_image_strips)
        # Compatibility alias used by older navigation code.
        self.frame_list = self.thermal_frame_list
        # itemClicked is required because Replay rendering automatically tracks
        # the current thumbnail.  Clicking that already-selected thumbnail does
        # not emit currentRowChanged, which previously made Anatomy/Thermal look
        # dead.  currentRowChanged is retained for keyboard navigation.
        for strip in (self.planning_frame_list, self.anatomy_frame_list, self.thermal_frame_list):
            # itemPressed fires before selection bookkeeping and is the most
            # reliable mouse path in packaged Qt builds. itemActivated keeps
            # keyboard/double-click access. Do not depend on currentRowChanged:
            # the replay renderer changes current rows programmatically.
            strip.itemPressed.connect(lambda item, owner=strip: self._unified_image_item_selected(owner, item))
            strip.itemClicked.connect(lambda item, owner=strip: self._unified_image_item_selected(owner, item))
            strip.itemActivated.connect(lambda item, owner=strip: self._unified_image_item_selected(owner, item))
        navigator_box = QGroupBox("Planning / Anatomy / Thermal Images")
        nav_layout = QGridLayout(navigator_box); nav_layout.setContentsMargins(3,8,3,3); nav_layout.setSpacing(2)
        for row,(label,combo,strip) in enumerate((("Row 1",self.planning_type_combo,self.planning_frame_list),("Row 2",self.anatomy_type_combo,self.anatomy_frame_list),("Row 3",self.thermal_type_combo,self.thermal_frame_list))):
            box=QWidget(); bl=QVBoxLayout(box); bl.setContentsMargins(0,0,0,0); bl.setSpacing(2); bl.addWidget(QLabel(label)); bl.addWidget(combo)
            nav_layout.addWidget(box,row,0); nav_layout.addWidget(strip,row,1)
        navigator_box.setMinimumHeight(145)
        nav_layout.setColumnStretch(1, 1)
        self._main_image_mode = "thermal"
        self._planning_display_arrays = []

        self.temperature_plot = pg.PlotWidget()
        self.temperature_plot.setLabel("left", "Temperature", units="°C")
        self.temperature_plot.setLabel("bottom", "MR acquisition time", units="sec")
        self.temperature_plot.showGrid(x=True, y=True, alpha=.28)
        self.temperature_plot.setYRange(40, 60, padding=0)
        self.temperature_plot.getAxis("left").setTickSpacing(major=2, minor=1)
        # Workstation-style temperature bands remain behind every curve.
        self.temperature_bands = []
        for low, high, rgba in (
            (40, 44, (70, 105, 150, 35)),
            (44, 48, (70, 145, 120, 35)),
            (48, 52, (205, 170, 35, 38)),
            (52, 56, (220, 105, 25, 42)),
            (56, 60, (190, 30, 30, 46)),
        ):
            band = pg.LinearRegionItem(values=(low, high), orientation="horizontal", movable=False, brush=pg.mkBrush(*rgba), pen=pg.mkPen(None))
            band.setZValue(-20)
            self.temperature_plot.addItem(band)
            self.temperature_bands.append(band)
        self.max_temperature_curve = self.temperature_plot.plot(pen=pg.mkPen("#ff3b30", width=3), name="Max")
        self.mean_temperature_curve = self.temperature_plot.plot(pen=pg.mkPen("#49e36b", width=2.5), name="ROI Average")
        self.cursor_temperature_curve = self.temperature_plot.plot(pen=pg.mkPen("#b98cff", width=1.6, style=Qt.PenStyle.DashLine), name="Cursor")
        self.temperature_cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#00bfff", width=1.5))
        self.temperature_plot.addItem(self.temperature_cursor)
        self.temperature_plot.scene().sigMouseClicked.connect(self._temperature_plot_clicked)
        self.temperature_hover_text = pg.TextItem(anchor=(0, 1), color="#ffffff", fill=pg.mkBrush(0, 0, 0, 190))
        self.temperature_hover_text.setZValue(50); self.temperature_hover_text.hide(); self.temperature_plot.addItem(self.temperature_hover_text)
        self.temperature_hover_proxy = pg.SignalProxy(self.temperature_plot.scene().sigMouseMoved, rateLimit=45, slot=self._temperature_plot_hovered)
        self._updating_temperature_range = False
        self.temperature_plot.plotItem.vb.sigRangeChanged.connect(self._temperature_range_changed_by_user)

        self.spectrum_plot = pg.PlotWidget()
        self.spectrum_plot.setLabel("left", "Relative Amplitude")
        self.spectrum_plot.setLabel("bottom", "Frequency", units="MHz")
        self.spectrum_plot.showGrid(x=True, y=True, alpha=.24)
        self.spectrum_plot.setXRange(0.2, 0.8, padding=0)
        self.spectrum_plot.setYRange(0.0, 4.0, padding=0)
        self.spectrum_hover_text = pg.TextItem(anchor=(0, 1), color="#ffffff", fill=pg.mkBrush(0, 0, 0, 205))
        self.spectrum_hover_text.setZValue(100); self.spectrum_hover_text.hide(); self.spectrum_plot.addItem(self.spectrum_hover_text)
        self.spectrum_hover_series = []
        self.spectrum_hover_proxy = pg.SignalProxy(self.spectrum_plot.scene().sigMouseMoved, rateLimit=45, slot=self._spectrum_plot_hovered)
        self.spectrum_plot.plotItem.vb.sigRangeChanged.connect(lambda *_: self._remember_chart_range("spectrum", self.spectrum_plot))

        self.graph_split = QSplitter(Qt.Orientation.Horizontal)
        self.temperature_panel=self._chart_panel("Temperature Trend (ROI)",self.temperature_plot,"temperature")
        self.spectrum_panel=self._chart_panel("Acoustic Spectrum (Current Frame)",self.spectrum_plot,"spectrum")
        self.graph_split.addWidget(self.temperature_panel); self.graph_split.addWidget(self.spectrum_panel)
        # Temperature is the primary replay trend; spectrum is contextual data
        # for the selected frame.  C0045 incorrectly made spectrum wider (3:4).
        self.graph_split.setStretchFactor(0, 65); self.graph_split.setStretchFactor(1, 35)
        self.graph_split.setChildrenCollapsible(False)
        self.temperature_panel.setMinimumWidth(420)
        self.spectrum_panel.setMinimumWidth(280)
        self.graph_split.setSizes([650, 350])
        self.graph_split.setMinimumHeight(155)

        # FUS workstation-style Power and Score trend. Current values are drawn inside the chart.
        self.acoustic_control_plot = pg.PlotWidget()
        self.acoustic_control_plot.setMinimumHeight(150)
        self.acoustic_control_plot.setLabel("left", "Power / Score", units="%")
        self.acoustic_control_plot.setLabel("bottom", "MR acquisition time", units="sec")
        self.acoustic_control_plot.setYRange(0.0, 110.0, padding=0)
        self.acoustic_control_plot.showGrid(x=True, y=True, alpha=.22)
        self.acoustic_power_curve = self.acoustic_control_plot.plot(pen=pg.mkPen("#58f26a", width=2.3), name="Power %")
        self.acoustic_score_curve = self.acoustic_control_plot.plot(pen=pg.mkPen("#ff9d22", width=2.3), name="Score")
        self.acoustic_control_cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#00bfff", width=1.3))
        self.acoustic_control_plot.addItem(self.acoustic_control_cursor)
        self.acoustic_control_plot.scene().sigMouseClicked.connect(self._acoustic_plot_clicked)
        self.acoustic_hover_text = pg.TextItem(anchor=(0, 1), color="#ffffff", fill=pg.mkBrush(0, 0, 0, 205))
        self.acoustic_hover_text.setZValue(80); self.acoustic_hover_text.hide(); self.acoustic_control_plot.addItem(self.acoustic_hover_text)
        self.acoustic_hover_proxy = pg.SignalProxy(self.acoustic_control_plot.scene().sigMouseMoved, rateLimit=45, slot=self._acoustic_plot_hovered)
        self.acoustic_power_text = pg.TextItem("Power: --", color="#58f26a", anchor=(1, 1), fill=pg.mkBrush(0, 0, 0, 150))
        self.acoustic_score_text = pg.TextItem("Score: --", color="#ff9d22", anchor=(1, 0), fill=pg.mkBrush(0, 0, 0, 150))
        self.acoustic_power_text.setZValue(20); self.acoustic_score_text.setZValue(20)
        self.acoustic_control_plot.addItem(self.acoustic_power_text); self.acoustic_control_plot.addItem(self.acoustic_score_text)
        self.acoustic_power_value = QLabel("Unavailable")
        self.acoustic_score_value = QLabel("Unavailable")
        self.acoustic_cavitation_value = QLabel("Unavailable")
        for w in (self.acoustic_power_value, self.acoustic_score_value, self.acoustic_cavitation_value):
            w.hide()

        self.waterfall_replay_plot = pg.PlotWidget()
        self.waterfall_replay_plot.setLabel("left", "Frequency", units="MHz")
        self.waterfall_replay_plot.setLabel("bottom", "Replay time", units="sec")
        self.waterfall_replay_plot.setTitle("")
        self.waterfall_replay_image = pg.ImageItem(axisOrder="row-major")
        self.waterfall_replay_plot.addItem(self.waterfall_replay_image)
        waterfall_colors = np.array([[0,0,25,255],[0,55,170,255],[0,210,255,255],[255,235,0,255],[255,75,0,255],[255,255,255,255]], dtype=np.ubyte)
        waterfall_positions = np.linspace(0.0, 1.0, len(waterfall_colors))
        self.waterfall_replay_image.setLookupTable(pg.ColorMap(waterfall_positions, waterfall_colors).getLookupTable(0.0, 1.0, 256))
        self.waterfall_replay_cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("w", width=1.5))
        self.waterfall_replay_plot.addItem(self.waterfall_replay_cursor)

        # Compact CH popup: single, multiple, or all channels without wasting chart height.
        self.channel_actions = {}
        self.channel_button = QToolButton()
        self.channel_button.setText("CH")
        self.channel_button.setToolTip("Select one, multiple, or all hydrophone channels")
        self.channel_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.channel_menu = QMenu(self.channel_button)
        self.all_channels_action = QAction("All Channels", self.channel_menu)
        self.all_channels_action.setCheckable(True); self.all_channels_action.setChecked(False)
        self.all_channels_action.toggled.connect(self._toggle_all_channels)
        self.channel_menu.addAction(self.all_channels_action)
        self.channel_menu.addSeparator()
        self.channel_button.setMenu(self.channel_menu)
        self.current_spectrum_label = QLabel("Spectrum: waiting")
        self.current_spectrum_label.setObjectName("CurrentValue")
        self.current_spectrum_label.setMaximumHeight(20)
        spectrum_layout = self.spectrum_panel.layout()
        channel_row = QHBoxLayout(); channel_row.setContentsMargins(0,0,0,0); channel_row.setSpacing(4)
        self.cpc_button = QPushButton("CPC OFF")
        self.cpc_button.setCheckable(True)
        self.cpc_button.setChecked(False)
        self.cpc_button.setToolTip("Switch the main Acoustic Spectrum between Sonication SpectrumMsg and mapped CPC 8CH FFT data")
        self.cpc_button.show()
        self.cpc_button.toggled.connect(self._cpc_toggled)
        self.spectrum_mode_combo = QComboBox()
        self.spectrum_mode_combo.addItems(["Current", "Average", "Max Hold", "Baseline Δ"])
        self.spectrum_mode_combo.setCurrentText(self.chart_state.spectrum_mode)
        self.spectrum_mode_combo.setToolTip("Current frame, score-window average, max hold, or fixed-baseline delta")
        self.spectrum_mode_combo.currentTextChanged.connect(self._spectrum_mode_changed)
        channel_row.addWidget(self.channel_button); channel_row.addWidget(self.cpc_button); channel_row.addWidget(self.spectrum_mode_combo); channel_row.addWidget(self.current_spectrum_label); channel_row.addStretch(1)
        spectrum_layout.insertLayout(0, channel_row)
        acoustic_box = self._chart_panel("Power % / Score", self.acoustic_control_plot, "acoustic")
        self.waterfall_panel = self._chart_panel("Relative Acoustic Spectrum vs Replay Time", self.waterfall_replay_plot, "waterfall")

        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0)
        # A vertical splitter guarantees a real plotting viewport for Power/Score
        # on 1366x768 laptops; fixed minimums previously exceeded screen height.
        self.waterfall_panel.setVisible(False)
        self.lower_split=QSplitter(Qt.Orientation.Horizontal)
        self.lower_split.addWidget(acoustic_box); self.lower_split.setMinimumHeight(150)
        self.right_vertical_split = QSplitter(Qt.Orientation.Vertical)
        self.right_vertical_split.addWidget(navigator_box)
        self.right_vertical_split.addWidget(self.graph_split)
        self.right_vertical_split.addWidget(self.lower_split)
        for i in range(3): self.right_vertical_split.setCollapsible(i, False)
        self.right_vertical_split.setStretchFactor(0, 3)
        self.right_vertical_split.setStretchFactor(1, 4)
        self.right_vertical_split.setStretchFactor(2, 4)
        self.right_vertical_split.setSizes([190, 230, 210])
        rl.addWidget(self.right_vertical_split,1)

        self.top_split = QSplitter(Qt.Orientation.Horizontal)
        self.top_split.addWidget(left); self.top_split.addWidget(self.overlay); self.top_split.addWidget(right)
        self.top_split.setSizes([155,760,760]); self.top_split.setStretchFactor(1,5); self.top_split.setStretchFactor(2,4)

        self.first_btn=QPushButton("|<"); self.prev_btn=QPushButton("<"); self.play_btn=QPushButton("▶")
        self.next_btn=QPushButton(">"); self.last_btn=QPushButton(">|")
        self.first_btn.clicked.connect(lambda:self.set_frame(0)); self.prev_btn.clicked.connect(self.previous_frame)
        self.play_btn.clicked.connect(self.toggle_play); self.next_btn.clicked.connect(self.next_frame)
        self.last_btn.clicked.connect(lambda:self.set_frame(max(0,self.current.replay_frame_count-1) if self.current else 0))
        self.speed=QSpinBox(); self.speed.setRange(1,20); self.speed.setValue(5); self.speed.setSuffix(" fps"); self.speed.valueChanged.connect(self.speed_changed)
        self.workstation_replay_check = QCheckBox("Workstation replay")
        self.workstation_replay_check.setChecked(True)
        self.workstation_replay_check.setToolTip("Reveal acquired images and trends progressively, matching the treatment workstation recording")
        self.workstation_replay_check.toggled.connect(self._workstation_replay_toggled)
        self.frame_label=QLabel("Frame -/-"); self.frame_label.setObjectName("CurrentValue")
        self.sync_label=QLabel("Image / Temperature / Spectrum: waiting"); self.sync_label.setObjectName("CurrentValue")
        self.timeline=QSlider(Qt.Orientation.Horizontal); self.timeline.valueChanged.connect(self.slider_changed)
        controls=QHBoxLayout()
        for w in (self.first_btn,self.prev_btn,self.play_btn,self.next_btn,self.last_btn,QLabel("Speed"),self.speed,self.workstation_replay_check,self.frame_label): controls.addWidget(w)
        controls.addStretch(1); controls.addWidget(self.sync_label)
        bottom=QWidget(); bl=QVBoxLayout(bottom); bl.setContentsMargins(5,1,5,3); bl.addLayout(controls); bl.addWidget(self.timeline)

        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(2,2,2,2)
        layout.addLayout(top_bar); layout.addWidget(self.top_split,1); layout.addWidget(bottom,0)
        return page

    def _build_analysis_tab(self) -> QWidget:
        """Preserve earlier analysis work without allowing it to dominate Replay."""
        self.hydro_view = QComboBox()
        self.hydro_view.addItems(["Both", "Spectrum", "Waterfall"])
        self.hydro_view.currentIndexChanged.connect(self._hydro_layout_changed)
        self.hydro_arrangement = QComboBox()
        self.hydro_arrangement.addItems(["Overlay", "Stacked"])
        self.hydro_arrangement.currentIndexChanged.connect(lambda _: self._update_analysis_hydrophone())

        controls = QHBoxLayout()
        controls.addWidget(QLabel("View"))
        controls.addWidget(self.hydro_view)
        controls.addWidget(QLabel("Spectrum layout"))
        controls.addWidget(self.hydro_arrangement)
        controls.addStretch(1)

        self.analysis_spectrum_plot = pg.PlotWidget(title="Hydrophone Spectrum Analysis")
        self.analysis_spectrum_plot.setLabel("bottom", "Frequency", units="kHz")
        self.analysis_spectrum_plot.showGrid(x=True, y=True, alpha=.2)
        self.waterfall_plot = pg.PlotWidget(title="Hydrophone Waterfall")
        self.waterfall_plot.setLabel("left", "Spectrum frame / channel")
        self.waterfall_plot.setLabel("bottom", "Frequency", units="kHz")
        self.waterfall_image = pg.ImageItem()
        self.waterfall_plot.addItem(self.waterfall_image)
        self.waterfall_cursor = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("y", width=2))
        self.waterfall_plot.addItem(self.waterfall_cursor)

        self.hydro_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.hydro_splitter.addWidget(self.analysis_spectrum_plot)
        self.hydro_splitter.addWidget(self.waterfall_plot)
        self.hydro_splitter.setSizes([800, 800])

        info = QLabel(
            "The earlier acoustic-analysis work is preserved here. "
            "Replay-first synchronization is completed before further analysis expansion."
        )
        info.setWordWrap(True)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(info)
        layout.addLayout(controls)
        layout.addWidget(self.hydro_splitter, 1)
        return page

    def _build_planning_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        note = QLabel("Planning resources are extracted separately from Sonication replay frames. CT/SDR, pre-treatment MR, and registration data remain traceable to their source files.")
        note.setWordWrap(True); layout.addWidget(note)
        self.planning_table = QTableWidget(0, 5)
        self.planning_table.setHorizontalHeaderLabels(["Category", "Role", "Confidence", "File", "Notes"])
        self.planning_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.planning_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.planning_table, 1)
        return page

    def _build_hydrophone_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        self.hydrophone_note = QLabel("No sonication loaded")
        self.hydrophone_note.setWordWrap(True); layout.addWidget(self.hydrophone_note)
        self.hydrophone_table = QTableWidget(8, 4)
        self.hydrophone_table.setHorizontalHeaderLabels(["Hydrophone", "Decoded Frames", "Peak Amplitude", "Status"])
        self.hydrophone_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hydrophone_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.hydrophone_table, 1)
        return page

    def _update_planning_view(self):
        assets = list(getattr(self.package, "planning_assets", []) or []) if self.package else []
        self.planning_table.setRowCount(len(assets))
        for row, asset in enumerate(assets):
            values = [asset.category, asset.role, f"{asset.confidence:.0%}", str(asset.path.relative_to(self.package.workspace)), asset.notes]
            for col, value in enumerate(values):
                self.planning_table.setItem(row, col, QTableWidgetItem(str(value)))

    def _update_hydrophone_view(self):
        if not self.current or not self.package:
            return
        replay = self.hydrophone_replay_service.build(self.current, self.current.main_frequency_hz or self.package.main_frequency_hz or 650000.0)
        self.hydrophone_note.setText(replay.decoder_note)
        for row, channel in enumerate(replay.channels):
            peak = "-" if channel.peak_amplitude is None else f"{channel.peak_amplitude:.6g}"
            values = [channel.label, len(channel.frames), peak, "Available" if channel.frames else "No decoded record"]
            for col, value in enumerate(values):
                self.hydrophone_table.setItem(row, col, QTableWidgetItem(str(value)))

    def _open_hydrophone_window(self):
        if not self.package:
            QMessageBox.information(self, APP_NAME, "Load a treatment ZIP first.")
            return
        if self.hydrophone_window is None:
            self.hydrophone_window = EightHydrophoneWindow(self)
            self.hydrophone_window.sonicationRequested.connect(self._select_sonication_index)
        self.hydrophone_window.load_package(self.package, max(0, self.sonication_index))
        self.hydrophone_window.show(); self.hydrophone_window.raise_(); self.hydrophone_window.activateWindow()

    # --------------------------------------------------------------- Loading
    def open_zip(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open treatment or Sonication ZIP", "", "ZIP files (*.zip)")
        if file_name:
            self.load(Path(file_name))

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open treatment or Sonication folder")
        if folder:
            self.load(Path(folder))

    def load(self, source: Path):
        previous_workspace = self.package.workspace if self.package else None
        self._clear_replay_display()
        try:
            workspace = self.importer.open(source)
            package = self.discovery.discover(source, workspace)
            if not package.sonications:
                self.importer.release(workspace)
                QMessageBox.information(self, APP_NAME, "No compatible Sonication data found.")
                return
            self.package = package
            if previous_workspace is not None and previous_workspace != workspace:
                self.importer.release(previous_workspace)
        except Exception as exc:
            LOG.exception("Import failed")
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        self.hydrophone_calibration = self.hydrophone_calibration_service.read(self.package.workspace)
        self.spectrum_provider = SpectrumMsgAnalyzerAdapter(self.package.main_frequency_hz, self.hydrophone_calibration)
        self.sonication_index = 0
        self.replay_context.configure_study(len(self.package.sonications))
        # Diagnostics must consume the exact extracted workspace used by Replay.
        # Load it before selecting a sonication so all dependent windows share
        # one initialized study context.
        self.diagnostics_tab.load_study(self.package.workspace, self.package)
        self._update_planning_view()
        self.replay_context.configure_study(len(self.package.sonications))
        self._select_sonication_index(0)
        self.statusBar().showMessage(f"Loaded {len(self.package.sonications)} sonication(s); diagnostics validated")

    def _change_sonication(self, step: int):
        if not self.package or not self.package.sonications:
            return
        self._select_sonication_index((self.sonication_index + step) % len(self.package.sonications))

    def _select_sonication_index(self, index: int):
        if not self.package or not self.package.sonications:
            return
        self._clear_replay_display()
        self.sonication_index = max(0, min(index, len(self.package.sonications)-1))
        self.current = self.package.sonications[self.sonication_index]
        son_freq = self.current.main_frequency_hz or self.package.main_frequency_hz
        self.spectrum_provider = SpectrumMsgAnalyzerAdapter(son_freq, self.hydrophone_calibration)
        self.timer.stop(); self.play_btn.setText("▶")
        self.replay.clear_cache()
        self._load_spectrum_channels()
        spectrum_counts = {name: len(frames) for name, frames in self.spectrum_channels.items() if frames}
        self.snapshot_provider.bind_sonication(self.sonication_index, self.current, spectrum_counts)
        self.cursor_x = self.cursor_y = None
        self._prepare_common_timeline()
        self._build_temperature_trends()
        self._build_acoustic_trends()
        self._build_frame_navigator()
        # Every newly opened source/sonication starts from a clean, fitted view.
        # Pan/zoom/WLWW are then retained only for the current loaded session.
        self._overlay_session_view = None
        self._overlay_session_levels = None
        self._restore_overlay_session = False
        self._fit_overlay_next = True
        self.son_number_btn.setText(str(self.sonication_index + 1))
        self.son_number_btn.set_popup_text(self._sonication_popup_text())
        self._update_sonication_metadata()
        self.diagnostics_tab.select_sonication(self.sonication_index)
        if self.hydrophone_window is not None and self.hydrophone_window.isVisible():
            self.hydrophone_window.sync_sonication(self.sonication_index)
        # Display the first valid replay image immediately after loading.
        # Prefer the product-style thermal overlay when temperature data exists;
        # otherwise fall back to the anatomy MR image.
        self.frame_index = self._first_valid_replay_frame()
        initial_mode = "thermal" if self.current.temperature_frames else "anatomy"
        self._main_image_mode = initial_mode
        # Restore the RC1 synchronous runtime path. Context is retained as a
        # mirror, but the visible render no longer depends on signal delivery.
        self.replay_context.select_sonication(
            self.sonication_index, self.current.replay_frame_count, self.frame_index
        )
        self.set_frame(self.frame_index, display_mode=initial_mode)

    def _highest_average_frame(self):
        if not self.mean_temperature_trend:
            return 0
        values=np.asarray(self.mean_temperature_trend,float)
        return int(np.nanargmax(values)) if np.isfinite(values).any() else 0

    def select_sonication(self):
        return

    def _sonication_popup_text(self):
        if not self.current or not self.package:
            return "No sonication loaded"
        return (f"Sonication {self.sonication_index+1} / {len(self.package.sonications)}\n"
                f"Name: {self.current.name}\nFrames: {self.current.replay_frame_count}\n"
                f"Duration: {self._replay_duration_s():.3f} sec\n"
                f"Temperature RAW: {len(self.current.temperature_frames)}\n"
                f"Magnitude RAW: {len(self.current.magnitude_frames)}\n"
                f"SpectrumMsg: {len(self.current.spectrum_files)}\nACT: {len(self.current.act_files)}")

    # ---------------------------------------------------------- Synchronization
    def _prepare_common_timeline(self) -> None:
        self.current_timeline_duration_s = 0.0
        if not self.current or not self.package:
            return
        if self.current.replay_frame_count > 1:
            # Product Replay shows the complete MR acquisition window.  Exported
            # thermometry frames are approximately 3.4 s apart in this platform.
            self.current_timeline_duration_s = float(self.current.replay_frame_count - 1) * 3.4
        else:
            measured = self.acoustic_control_service.measured_duration_for_sonication(
                self.package.workspace, self.sonication_index
            )
            self.current_timeline_duration_s = float(measured or 0.0)

    def _build_temperature_trends(self):
        self.max_temperature_trend = []
        self.mean_temperature_trend = []
        self.delta_trend = []
        if not self.current:
            return
        for index in range(self.current.replay_frame_count):
            try:
                data = self.replay.frame(self.current, index)
                self.max_temperature_trend.append(data.maximum_temperature if data.maximum_temperature is not None else np.nan)
                self.mean_temperature_trend.append(data.mean_temperature if data.mean_temperature is not None else np.nan)
                self.delta_trend.append(data.maximum_delta_temperature if data.maximum_delta_temperature is not None else np.nan)
            except Exception:
                self.max_temperature_trend.append(np.nan)
                self.mean_temperature_trend.append(np.nan)
                self.delta_trend.append(np.nan)
        x = self._frame_time_axis(self.current.replay_frame_count)
        self.max_temperature_curve.setData(x, np.asarray(self.max_temperature_trend, float), connect="finite")
        self.mean_temperature_curve.setData(x, np.asarray(self.mean_temperature_trend, float), connect="finite")
        if len(x):
            self._fit_temperature_trend(force=not self.chart_state.temperature_user_zoomed)

    def _build_acoustic_trends(self):
        count = self.current.replay_frame_count if self.current else 0
        if not self.current or not self.package or count <= 0:
            self.acoustic_peaks = np.asarray([], dtype=float)
            self.acoustic_scores = np.asarray([], dtype=float)
            self.acoustic_control_trend = None
            self.acoustic_power_curve.setData([], [])
            self.acoustic_score_curve.setData([], [])
            return
        duration = self._index_to_seconds(max(count - 1, 0), count)
        trend = self.acoustic_control_service.trend_for_sonication(
            self.package.workspace, self.sonication_index, count, duration
        )
        self.acoustic_control_trend = trend
        self.acoustic_peaks = trend.power_percent
        self.acoustic_scores = trend.score_percent
        tx=np.asarray(trend.time_s,float); py=np.asarray(trend.power_percent,float); sy=np.asarray(trend.score_percent,float)
        if not np.isfinite(py).any() and self.current.planned_power_w is not None:
            # planned_power_w is an absolute Watt value, never a percentage.
            # Keep the percentage plot empty and expose the Watt value as annotation.
            py=np.full(tx.shape, np.nan, dtype=float)
            trend.power_percent=py
            trend.status=f"Measured Power % unavailable; planned power {float(self.current.planned_power_w):.1f} W"
        self.acoustic_power_curve.setData(tx, py, connect="finite")
        self.acoustic_score_curve.setData(tx, sy, connect="finite")
        finite = np.concatenate((trend.power_percent[np.isfinite(trend.power_percent)], trend.score_percent[np.isfinite(trend.score_percent)]))
        # Power and Score are percentages: keep a stable 0-110 % viewport.
        self.acoustic_control_plot.setYRange(0.0, 110.0, padding=0.0)
        if not np.isfinite(py).any() and self.current.planned_power_w is not None:
            self.acoustic_power_text.setText(f"Planned: {float(self.current.planned_power_w):.1f} W\nMeasured Power % unavailable")
        if trend.time_s.size:
            self.acoustic_control_plot.setXRange(float(np.nanmin(trend.time_s)), float(np.nanmax(trend.time_s) or 1.0), padding=0.01)
        self.acoustic_control_plot.enableAutoRange(axis='x', enable=False)
        if trend.source:
            self.acoustic_control_plot.setTitle("")
        else:
            self.acoustic_control_plot.setTitle("")

    def _ensure_acoustic_curve_items(self):
        """Recreate embedded Power/Score PlotDataItems when Qt loses them.

        Recreating the curves is more reliable than re-adding stale PlotDataItems
        after a popup has been opened or a sonication has changed.
        """
        for attr in ("acoustic_power_curve", "acoustic_score_curve"):
            item=getattr(self,attr,None)
            if item is not None:
                try: self.acoustic_control_plot.removeItem(item)
                except Exception: pass
        self.acoustic_power_curve=self.acoustic_control_plot.plot(pen=pg.mkPen("#58f26a",width=2.5),name="Power %")
        self.acoustic_score_curve=self.acoustic_control_plot.plot(pen=pg.mkPen("#ff9d22",width=2.5),name="Score")
        for item in (self.acoustic_control_cursor,self.acoustic_hover_text,self.acoustic_power_text,self.acoustic_score_text):
            try:
                if item not in self.acoustic_control_plot.items(): self.acoustic_control_plot.addItem(item)
            except Exception:
                try: self.acoustic_control_plot.addItem(item)
                except Exception: pass

    def _build_frame_navigator(self):
        for widget in (self.planning_frame_list, self.anatomy_frame_list, self.thermal_frame_list):
            widget.blockSignals(True); widget.clear()
        self._planning_display_arrays = []
        self._planning_assets_all = []
        self._anatomy_row_map = []
        self._thermal_row_map = []
        if not self.current:
            for widget in (self.planning_frame_list, self.anatomy_frame_list, self.thermal_frame_list): widget.blockSignals(False)
            return

        assets = list(getattr(self.package, "planning_assets", []) or []) if self.package else []
        categories = []
        for asset in assets:
            array = self._decode_planning_image(asset)
            category = self._planning_category(asset)
            label = f"{category.replace('Planning ', '')}\n{asset.path.name}"
            if array is not None:
                self._planning_assets_all.append((asset, array, label, category))
                if category not in categories: categories.append(category)
        # Row selectors are fixed and identical for all three rows.  Do not
        # repopulate the first combo from discovered categories because that
        # would remove the requested cross-row choices.

        for row, frame in enumerate(self.current.magnitude_frames):
            try:
                array = self.replay.raw.read_magnitude(frame.path)
                finite = np.asarray(array, float); finite = finite[np.isfinite(finite)]
                if not finite.size or float(np.nanstd(finite)) <= 1e-8: continue
                icon = self._array_icon(array)
            except Exception:
                continue
            item=QListWidgetItem(icon, f"MR {row+1}\n{frame.path.name}"); item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.anatomy_frame_list.addItem(item); self._anatomy_row_map.append(row)

        for row, frame in enumerate(self.current.temperature_frames):
            try:
                array = self.replay.raw.read_temperature(frame.path)
                finite = np.asarray(array, float); finite = finite[np.isfinite(finite)]
                # Empty/constant first thermal frames are acquisition placeholders, not images.
                if not finite.size or float(np.nanstd(finite)) <= 1e-8: continue
                icon = self._array_icon(array)
            except Exception:
                continue
            item=QListWidgetItem(icon, f"Temp {row+1}\n{frame.path.name}"); item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.thermal_frame_list.addItem(item); self._thermal_row_map.append(row)

        for widget in (self.planning_frame_list, self.anatomy_frame_list, self.thermal_frame_list): widget.blockSignals(False)
        self._rebuild_all_image_strips()

    def _all_image_entries(self):
        entries=[]
        planning_assets = list(getattr(self, "_planning_assets_all", []))
        verified_ct_available = any(
            category == "Planning CT" and getattr(asset, "field_index", None) == 16
            for asset, _array, _label, category in planning_assets
        )
        for asset,array,label,category in planning_assets:
            if category == "Planning CT":
                # Field 16 is the verified signed CT/HU stack.  Derived 512x512
                # fields are not mixed into the default CT volume because that
                # made the first displayed image look like CT had not loaded.
                if verified_ct_available and getattr(asset, "field_index", None) != 16:
                    continue
                mode = "planning_ct"
                slice_no = getattr(asset, "array_index", None)
                label = f"CT {slice_no + 1 if isinstance(slice_no, int) else '?'}\n{asset.path.name}"
            elif category == "Planning MR":
                mode = "planning_mr"
            else:
                continue
            entries.append((mode,array,label,None))
        if self.current:
            for row,frame in enumerate(self.current.magnitude_frames):
                try:
                    arr=self.replay.raw.read_magnitude(frame.path)
                    finite=np.asarray(arr,float); finite=finite[np.isfinite(finite)]
                    if finite.size and float(np.nanstd(finite))>1e-8: entries.append(("anatomy",arr,f"MR {row+1}\n{frame.path.name}",row))
                except Exception: pass
            for row,frame in enumerate(self.current.temperature_frames):
                try:
                    arr=self.replay.raw.read_temperature(frame.path)
                    finite=np.asarray(arr,float); finite=finite[np.isfinite(finite)]
                    if finite.size and float(np.nanstd(finite))>1e-8: entries.append(("thermal",arr,f"Temp {row+1}\n{frame.path.name}",row))
                except Exception: pass
        return entries

    def _rebuild_all_image_strips(self, *_):
        mapping={
            "Planning CT":{"planning_ct"},
            "Planning MR":{"planning_mr"},
            "Anatomy MR":{"anatomy"},
            "Thermal":{"thermal"},
            "All images":{"planning_ct","planning_mr","anatomy","thermal"},
        }
        entries=self._all_image_entries()
        for strip,combo in ((self.planning_frame_list,self.planning_type_combo),(self.anatomy_frame_list,self.anatomy_type_combo),(self.thermal_frame_list,self.thermal_type_combo)):
            strip.blockSignals(True); strip.clear()
            allowed=mapping.get(combo.currentText(),{"planning","anatomy","thermal"})
            for mode,array,label,source_index in entries:
                if mode not in allowed: continue
                item=QListWidgetItem(self._array_icon(array),label); item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                item.setData(Qt.ItemDataRole.UserRole,(mode,source_index,array,label)); strip.addItem(item)
            strip.blockSignals(False)
        # Planning rows are reference selectors only.  Rebuilding thumbnails must
        # never replace the live replay image with a CT/MR planning slice.
        # The main viewer remains owned by ReplayContext until the user explicitly
        # clicks a planning thumbnail.

    def _unified_image_item_selected(self, strip, item) -> None:
        """Activate a thumbnail even when it is already the current item."""
        if item is None:
            return
        self._activate_image_payload(item.data(Qt.ItemDataRole.UserRole))

    def _unified_image_selected(self, strip, row):
        if row < 0:
            return
        item = strip.item(row)
        if item is not None:
            self._activate_image_payload(item.data(Qt.ItemDataRole.UserRole))

    def _activate_image_payload(self, payload) -> None:
        """Display one thumbnail using an explicit source-to-replay mapping."""
        if not payload:
            return
        mode, source_index, array, label = payload
        if mode in {"planning_ct", "planning_mr"}:
            self._main_image_mode = mode
            self.overlay.set_hover_temperature(None)
            self.overlay.set_roi(None, None)
            self.overlay.set_overlay(array, None, fit=True)
            kind = "Planning CT" if mode == "planning_ct" else "Planning MR"
            self.frame_label.setText(f"{kind}: {label}")
            self.sync_label.setText(f"{kind} selected; replay arrows return to live MR")
            return
        if not self.current or source_index is None:
            return
        series_count = len(self.current.magnitude_frames) if mode == "anatomy" else len(self.current.temperature_frames)
        replay_index = self._map_data_to_replay(int(source_index), max(1, series_count), max(1, self.current.replay_frame_count))
        self._main_image_mode = mode
        # Immediate visual acknowledgement from the exact thumbnail payload.
        # This bypasses every mapping/cache layer, then the synchronized replay
        # render below replaces it with the canonical frame data.
        if mode == "anatomy":
            finite = np.asarray(array, float)
            vals = finite[np.isfinite(finite)]
            levels = tuple(map(float, np.percentile(vals, [2.0, 98.5]))) if vals.size else None
            self.overlay.set_hover_temperature(None)
            self.overlay.set_roi(None, None)
            self.overlay.set_overlay(array, None, levels, fit=True)
        else:
            # Thermal thumbnails are temperature arrays. Use the corresponding
            # magnitude frame as anatomy background when available.
            mag = None
            if self.current.magnitude_frames:
                mi = self._map_replay_to_data(replay_index, self.current.replay_frame_count, len(self.current.magnitude_frames))
                try:
                    mag = self.replay.raw.read_magnitude(self.current.magnitude_frames[mi].path)
                except Exception:
                    mag = None
            levels = self._temperature_levels(array)
            lut = self._temperature_lut_with_red_threshold(*(levels or (35.0, 60.0)))
            self.overlay.set_overlay(mag, array, None, levels, lut, self.overlay_opacity.value()/100.0, fit=True)
        self.set_frame(replay_index, display_mode=mode)

    def _activate_replay_mode_for_navigation(self) -> None:
        """Return the main viewer from a planning reference to live replay.

        Planning thumbnails are intentionally static references.  Timeline,
        arrows, wheel and playback always control the sonication replay and must
        therefore restore Thermal (or Anatomy when thermometry is unavailable).
        """
        if self._main_image_mode in {"planning", "planning_ct", "planning_mr"}:
            self._main_image_mode = "thermal" if self.current and self.current.temperature_frames else "anatomy"
            if hasattr(self, "planning_frame_list"):
                self.planning_frame_list.blockSignals(True)
                self.planning_frame_list.setCurrentRow(-1)
                self.planning_frame_list.blockSignals(False)
            self._fit_overlay_next = True

    def set_frame(self, index: int, display_mode: str | None = None):
        """Synchronously decode and render one live replay frame.

        This restores the direct RC1 behavior that previously worked. The
        central image, thumbnails, temperature cursor, acoustic spectrum and
        cards are updated in one call. ReplayContext is only a state mirror.
        """
        if not self.current:
            return
        if display_mode is None:
            self._activate_replay_mode_for_navigation()
        else:
            self._main_image_mode = display_mode
        count = max(1, int(self.current.replay_frame_count))
        target = max(0, min(int(index), count - 1))
        try:
            data = self.replay.frame(self.current, target)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Unable to decode frame\n{exc}")
            return

        self.frame_index = int(data.replay_index)
        try:
            self.replay_context.select_frame(self.frame_index)
            snapshot = self.snapshot_provider.resolve(self.replay_context.selection)
        except Exception:
            snapshot = None
        seconds = self._index_to_seconds(self.frame_index, count)

        self.timeline.blockSignals(True)
        self.timeline.setRange(0, count - 1)
        self.timeline.setValue(self.frame_index)
        self.timeline.blockSignals(False)

        if self.current.temperature_frames:
            ti_source = self.replay.raw.normalize_index(self.frame_index, count, len(self.current.temperature_frames))
            ti = min(range(len(self._thermal_row_map)), key=lambda i: abs(self._thermal_row_map[i] - ti_source)) if self._thermal_row_map else -1
            self.thermal_frame_list.blockSignals(True)
            self.thermal_frame_list.setCurrentRow(ti)
            self.thermal_frame_list.blockSignals(False)
        if self.current.magnitude_frames:
            mi_source = self.replay.raw.normalize_index(self.frame_index, count, len(self.current.magnitude_frames))
            mi = min(range(len(self._anatomy_row_map)), key=lambda i: abs(self._anatomy_row_map[i] - mi_source)) if self._anatomy_row_map else -1
            self.anatomy_frame_list.blockSignals(True)
            self.anatomy_frame_list.setCurrentRow(mi)
            self.anatomy_frame_list.blockSignals(False)

        self.frame_label.setText(
            f"{self._main_image_mode.upper()} | MR acquisition: {seconds:.2f} sec | "
            f"Frame {self.frame_index + 1}/{count} | "
            f"MR {data.magnitude_index + 1 if data.magnitude_index is not None else '-'} | "
            f"Temp {data.temperature_index + 1 if data.temperature_index is not None else '-'}"
        )
        self.temperature_cursor.setPos(seconds)
        if not self.chart_state.temperature_user_zoomed:
            self._fit_temperature_trend(force=True)

        magnitude_levels = self._overlay_session_levels
        if magnitude_levels is None and data.magnitude is not None:
            finite_mag = np.asarray(data.magnitude, float)
            finite_mag = finite_mag[np.isfinite(finite_mag)]
            if finite_mag.size:
                low, high = np.percentile(finite_mag, [2.0, 98.5])
                if high <= low:
                    high = low + 1.0
                magnitude_levels = (float(low), float(high))

        hotspot = (data.hotspot_x, data.hotspot_y) if data.hotspot_x is not None else None
        hotspot_text = None
        if data.maximum_temperature is not None:
            hotspot_text = f"Max = {data.maximum_temperature:.1f} °C\nAvg = {data.mean_temperature:.1f} °C"
        investigation = self.temperature_display_mode.startswith("Δ")
        shown = data.temperature_delta if investigation else data.temperature
        levels = self._delta_levels(shown) if investigation else self._temperature_levels(shown)
        if investigation:
            lut = pg.colormap.get("CET-L4").getLookupTable(0, 1, 256)
        else:
            low, high = levels if levels is not None else (40.0, 60.0)
            lut = self._temperature_lut_with_red_threshold(low, high)

        if self._main_image_mode == "anatomy":
            shown = None
            self.overlay.set_roi(None, None)
            self.overlay.set_hover_temperature(None)
        else:
            self.overlay.set_roi(data.roi_center_x, data.roi_center_y, data.roi_radius, data.roi_width, data.roi_height)
            self.overlay.set_hover_temperature(shown)

        self.overlay.set_overlay(
            data.magnitude, shown, magnitude_levels, levels, lut,
            self.overlay_opacity.value() / 100.0,
            hotspot, hotspot_text, None, fit=self._fit_overlay_next,
        )
        self._fit_overlay_next = False
        if self._restore_overlay_session and self._overlay_session_view:
            self.overlay.set_view_range(self._overlay_session_view)
        if self._restore_overlay_session and self._overlay_session_levels:
            self.overlay.set_magnitude_levels(self._overlay_session_levels)
        self._restore_overlay_session = True
        self.baseline_label.setText(
            f"Source: {data.temperature_source}\nReference: {data.reference_temperature:.1f} °C\nROI: {data.roi_source}"
        )

        if snapshot is not None:
            spectrum_index, spectrum_count = self._update_replay_spectrum(snapshot)
        else:
            spectrum_index, spectrum_count = None, 0
        self._update_analysis_hydrophone()
        self._update_info_window(data, count, spectrum_index, spectrum_count)
        self._update_acoustic_cards(data)
        self._update_cursor_for_frame(data)
        self._apply_workstation_replay_behavior(data, count)
        self._refresh_chart_popups()
        self.sync_label.setText(
            f"Image {self.frame_index + 1}/{count} | "
            f"Temperature {data.temperature_index + 1 if data.temperature_index is not None else '-'} | "
            f"Spectrum {spectrum_index + 1 if spectrum_index is not None else '-'}/{spectrum_count or '-'} | "
            f"Phase: {self._workstation_phase}"
        )

    def _workstation_replay_toggled(self, checked: bool) -> None:
        self.workstation_replay_enabled = bool(checked)
        if self.current:
            self.set_frame(self.frame_index, display_mode=self._main_image_mode)

    def _workstation_phase_for_frame(self, data, count: int) -> str:
        """Derive a stable acquisition/heating/cooling phase for replay UI.

        The export does not always contain explicit workstation state markers,
        so the phase is inferred conservatively from measured power and the
        temperature trend.  It is display metadata only and never changes the
        decoded data.
        """
        index = int(getattr(data, "replay_index", self.frame_index) or 0)
        if index <= 0:
            return "MR acquisition"
        power = np.nan
        if getattr(self, "acoustic_control_trend", None) is not None:
            arr = np.asarray(self.acoustic_control_trend.power_percent, float)
            if arr.size:
                power = arr[min(index, arr.size - 1)]
        values = np.asarray(self.max_temperature_trend, float)
        current = values[min(index, values.size - 1)] if values.size else np.nan
        previous = values[min(max(index - 1, 0), values.size - 1)] if values.size else np.nan
        if np.isfinite(power) and power > 3.0:
            return "Sonication"
        if np.isfinite(current) and np.isfinite(previous):
            if current > previous + 0.15:
                return "Heating"
            if current < previous - 0.15:
                return "Cooling"
        if index >= max(0, count - 1):
            return "Complete"
        return "Post acquisition"

    def _apply_workstation_replay_behavior(self, data, count: int) -> None:
        """Mirror the time-progressive behavior seen in the reference video.

        * Trends reveal only samples acquired up to the selected frame.
        * Current Anatomy/Thermal thumbnails remain visible and auto-scroll.
        * Main image stays in live Anatomy/Thermal replay while navigating.
        * Status reports the current acquisition/heating/cooling phase.
        """
        self._workstation_phase = self._workstation_phase_for_frame(data, count)
        if not getattr(self, "workstation_replay_enabled", True):
            # Restore complete trends when progressive replay is disabled.
            tx = self._frame_time_axis(count)
            self.max_temperature_curve.setData(tx, np.asarray(self.max_temperature_trend, float), connect="finite")
            self.mean_temperature_curve.setData(tx, np.asarray(self.mean_temperature_trend, float), connect="finite")
            trend = getattr(self, "acoustic_control_trend", None)
            if trend is not None:
                self.acoustic_power_curve.setData(np.asarray(trend.time_s, float), np.asarray(trend.power_percent, float), connect="finite")
                self.acoustic_score_curve.setData(np.asarray(trend.time_s, float), np.asarray(trend.score_percent, float), connect="finite")
            return

        end = min(max(0, self.frame_index) + 1, count)
        tx = self._frame_time_axis(count)[:end]
        self.max_temperature_curve.setData(tx, np.asarray(self.max_temperature_trend, float)[:end], connect="finite")
        self.mean_temperature_curve.setData(tx, np.asarray(self.mean_temperature_trend, float)[:end], connect="finite")
        if self.cursor_temperature_trend:
            self.cursor_temperature_curve.setData(tx, np.asarray(self.cursor_temperature_trend, float)[:end], connect="finite")

        trend = getattr(self, "acoustic_control_trend", None)
        if trend is not None and np.asarray(trend.time_s).size:
            current_s = self._index_to_seconds(self.frame_index, count)
            mask = np.asarray(trend.time_s, float) <= current_s + 1e-9
            self.acoustic_power_curve.setData(np.asarray(trend.time_s, float)[mask], np.asarray(trend.power_percent, float)[mask], connect="finite")
            self.acoustic_score_curve.setData(np.asarray(trend.time_s, float)[mask], np.asarray(trend.score_percent, float)[mask], connect="finite")

        for strip in (getattr(self, "anatomy_frame_list", None), getattr(self, "thermal_frame_list", None)):
            if strip is None or strip.count() <= 0:
                continue
            row = strip.currentRow()
            if row >= 0:
                item = strip.item(row)
                if item is not None:
                    strip.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)

        self.statusBar().showMessage(
            f"Replay {self.frame_index + 1}/{count} · {self._workstation_phase} · "
            f"{self._index_to_seconds(self.frame_index, count):.1f} sec"
        )

    def _update_replay_spectrum(self, snapshot: ReplayFrameSnapshot):
        replay_count = snapshot.selection.frame_count
        selected = self._selected_channels()
        seconds = snapshot.elapsed_seconds
        main_frequency = ((self.current.main_frequency_hz if self.current else None) or
                          (self.package.main_frequency_hz if self.package else None))
        saved_x = self.chart_state.x_ranges.get("spectrum")
        saved_y = self.chart_state.y_ranges.get("spectrum")
        result = self.current_spectrum_renderer.render(
            self.spectrum_plot, self.spectrum_channels, selected,
            self.frame_index, replay_count, self._channel_colors,
            main_frequency, self._map_replay_to_data, seconds,
            mode=self.chart_state.spectrum_mode,
            average_window=self.chart_state.spectrum_average_window,
            frame_indices=dict(snapshot.spectrum_indices),
        )
        self.spectrum_plot.addItem(self.spectrum_hover_text)
        if saved_x is not None:
            self.spectrum_plot.setXRange(*saved_x, padding=0)
        if saved_y is not None:
            self.spectrum_plot.setYRange(*saved_y, padding=0)
        self.spectrum_hover_series = result.series
        first_index = None
        first_count = 0
        statuses = []
        self._spectrum_frame = None
        for channel in selected:
            frames = self.spectrum_channels.get(channel, [])
            if not frames or channel not in result.frame_indices:
                continue
            idx = result.frame_indices[channel]
            statuses.append(f"{channel}:{idx + 1}/{len(frames)}")
            if first_index is None:
                first_index, first_count = idx, len(frames)
                self._spectrum_frame = frames[idx]
        self._spectrum_status = "; ".join(statuses) if statuses else "No SpectrumMsg"
        metric_text = ""
        if result.metrics:
            metric_text = (f" | Sub {result.metrics.get('subharmonic',0.0):.3f}"
                           f" Ultra {result.metrics.get('ultraharmonic',0.0):.3f}"
                           f" BB {result.metrics.get('broadband',0.0):.3f}")
        calibration_text = "CAL ON" if self.hydrophone_calibration is not None and self.hydrophone_calibration.available else "CAL OFF"
        source_text = "CPC" if self.cpc_enabled else "SpectrumMsg"
        self.current_spectrum_label.setText(f"Spectrum [{source_text} / {calibration_text}]: {self._spectrum_status}{metric_text}")
        return first_index, first_count

    def _update_analysis_hydrophone(self):
        if not hasattr(self, "analysis_spectrum_plot"):
            return
        self.analysis_spectrum_plot.clear()
        selected = self._selected_channels()
        replay_count = self.current.replay_frame_count if self.current else 1
        colors = ["#00bfff", "#ffcc00", "#ff66cc", "#66ff66", "#ff8844", "#cccccc"]
        stacked = self.hydro_arrangement.currentText() == "Stacked"
        for channel_index, channel in enumerate(selected):
            frames = self.spectrum_channels.get(channel, [])
            if not frames:
                continue
            spectrum_index = self._map_replay_to_data(self.frame_index, replay_count, len(frames))
            frame = frames[spectrum_index]
            x = np.asarray(frame.frequency, float) / 1000.0
            y = np.asarray(frame.amplitude, float)
            if stacked and y.size:
                span = max(1.0, float(np.nanmax(y) - np.nanmin(y)))
                y = y - channel_index * span * 1.2
            self.analysis_spectrum_plot.plot(x, y, pen=pg.mkPen(colors[channel_index % len(colors)], width=1.5))
        self._add_spectrum_reference_lines(self.analysis_spectrum_plot, mhz=False)
        self._update_waterfall()

    def _update_waterfall(self):
        selected = self._selected_channels()
        blocks = []
        max_columns = 0
        x_max = 1.0
        current_row = 0
        row_offset = 0
        replay_count = self.current.replay_frame_count if self.current else 1
        for channel in selected:
            frames = self.spectrum_channels.get(channel, [])
            rows = []
            for frame in frames:
                amplitude = np.asarray(frame.amplitude, float)
                if amplitude.size:
                    rows.append(amplitude)
                    max_columns = max(max_columns, amplitude.size)
                    if frame.frequency:
                        x_max = max(x_max, float(frame.frequency[-1]) / 1000.0)
            if rows:
                if not blocks:
                    current_row = row_offset + self._map_replay_to_data(self.frame_index, replay_count, len(rows))
                blocks.append(rows)
                row_offset += len(rows) + 2
        if not blocks or max_columns == 0:
            self.waterfall_image.setImage(np.empty((0, 0)))
            return
        bands = []
        for rows in blocks:
            padded = np.full((len(rows), max_columns), np.nan)
            for row_index, row in enumerate(rows):
                padded[row_index, : len(row)] = row
            bands.append(padded)
            bands.append(np.full((2, max_columns), np.nan))
        image = np.vstack(bands[:-1])
        finite = image[np.isfinite(image)]
        if finite.size:
            low, high = np.percentile(finite, [2, 98])
            self.waterfall_image.setImage(image, autoLevels=False, levels=(float(low), float(high)))
        else:
            self.waterfall_image.setImage(image)
        self.waterfall_image.setRect(QRectF(0, 0, x_max, image.shape[0]))
        self.waterfall_plot.setYRange(0, image.shape[0], padding=0)
        self.waterfall_cursor.setPos(current_row)

    def _threshold_changed(self, value: int):
        self.threshold_value.setText(f"Red starts at {value} °C")
        self.set_frame(self.frame_index)

    def _overlay_cursor_moved(self, x: float, y: float):
        self.cursor_x, self.cursor_y = x, y
        self._rebuild_cursor_temperature_trend()
        self.set_frame(self.frame_index)

    def _rebuild_cursor_temperature_trend(self):
        self.cursor_temperature_trend = []
        if not self.current or self.cursor_x is None or self.cursor_y is None:
            self.cursor_temperature_curve.setData([], [])
            return
        for i in range(self.current.replay_frame_count):
            try:
                data = self.replay.frame(self.current, i)
                arr = data.temperature
                if arr is None:
                    self.cursor_temperature_trend.append(np.nan); continue
                xi = int(np.clip(round(self.cursor_x), 0, arr.shape[1]-1))
                yi = int(np.clip(round(self.cursor_y), 0, arr.shape[0]-1))
                self.cursor_temperature_trend.append(float(arr[yi, xi]))
            except Exception:
                self.cursor_temperature_trend.append(np.nan)
        self.cursor_temperature_curve.setData(self._frame_time_axis(len(self.cursor_temperature_trend)), np.asarray(self.cursor_temperature_trend,float))

    def _update_cursor_for_frame(self, data):
        arr = data.temperature
        if arr is None:
            self.cursor_temperature_label.setText("Cursor Temperature: --")
            return
        if self.cursor_x is None or self.cursor_y is None:
            self.cursor_temperature_label.setText("Cursor Temperature: click or drag the small cyan target")
            return
        xi = int(np.clip(round(self.cursor_x),0,arr.shape[1]-1)); yi = int(np.clip(round(self.cursor_y),0,arr.shape[0]-1))
        value=float(arr[yi,xi])
        self.overlay.set_cursor(self.cursor_x,self.cursor_y,f"T {value:.1f} °C\nX {xi}  Y {yi}")
        self.cursor_temperature_label.setText(f"Cursor Temperature\nT: {value:.1f} °C\nX: {xi} px\nY: {yi} px")

    def _show_info_window(self):
        if self.info_window.isVisible(): return
        self.info_window.show(); self.info_window.raise_(); self.info_window.activateWindow()

    def _show_mr_window(self):
        if self.mr_window.isVisible(): return
        self.mr_window.show(); self.mr_window.raise_(); self.mr_window.activateWindow()

    def _show_scan_window(self):
        if self.scan_window.isVisible(): return
        self.scan_window.show(); self.scan_window.raise_(); self.scan_window.activateWindow()

    def _show_xd_window(self):
        if self.current is not None and self.package is not None:
            self.xd_window.set_data(self.skull_measures_service.find_and_read(
                self.current.folder, self.sonication_index + 1, self.package.workspace
            ))
        if self.xd_window.isVisible():
            self.xd_window.raise_(); self.xd_window.activateWindow(); return
        self.xd_window.show(); self.xd_window.raise_(); self.xd_window.activateWindow()

    def _update_sonication_metadata(self):
        if not self.current or not self.package: return
        self.current_metadata=self.metadata_service.read(self.current,self.package,self.sonication_index+1)
        for key,label in self.summary_value_labels.items(): label.setText(self.current_metadata.summary.get(key,"Unavailable"))
        mr_rows = list(self.current_metadata.mr or [])
        scan_rows = list(self.current_metadata.scan or [])
        if not mr_rows:
            mr_rows = [
                ("Sonication", self.current.name),
                ("Magnitude RAW files", len(self.current.magnitude_frames)),
                ("Temperature RAW files", len(self.current.temperature_frames)),
                ("Main frequency", f"{((self.current.main_frequency_hz or self.package.main_frequency_hz or 0)/1_000_000):.3f} MHz"),
                ("Source folder", str(self.current.folder)),
            ]
        if not scan_rows:
            scan_rows = [
                ("Replay frames", self.current.replay_frame_count),
                ("Magnitude frames", len(self.current.magnitude_frames)),
                ("Temperature frames", len(self.current.temperature_frames)),
                ("Spectrum files", len(self.current.spectrum_files)),
                ("ACT files", len(self.current.act_files)),
            ]
        self.mr_window.update_rows(mr_rows)
        self.scan_window.update_rows(scan_rows)
        self.xd_window.set_data(self.skull_measures_service.find_and_read(self.current.folder, self.sonication_index + 1, self.package.workspace))

    def _update_info_window(self, data, count, spectrum_index, spectrum_count):
        frequency = ((self.current.main_frequency_hz if self.current else None) or (self.package.main_frequency_hz if self.package else 0.0)) / 1_000_000.0
        summary = self.current_metadata.summary if self.current_metadata else {}
        rows=[
            ("Sonication No.", f"{self.sonication_index+1} / {len(self.package.sonications) if self.package else '-'}"),
            ("Orientation", summary.get("Orientation", "Unavailable")),
            ("Frequency Direction", summary.get("Frequency Dir", "Unavailable")),
            ("Power", summary.get("Power", "Unavailable")),
            ("Duration", summary.get("Duration", "Unavailable")),
            ("Energy", summary.get("Energy", "Unavailable")),
            ("Hotspot Check", summary.get("Hotspot Check", "Unavailable")),
            ("Name", self.current.name if self.current else "-"),
            ("Frequency", f"{frequency:.3f} MHz"),
            ("Replay Frame", f"{self.frame_index+1}/{count}"),
            ("Temperature RAW", data.temperature_index+1 if data.temperature_index is not None else "-"),
            ("SpectrumMsg", f"{spectrum_index+1 if spectrum_index is not None else '-'}/{spectrum_count or '-'}"),
            ("Temperature Source", data.temperature_source),
            ("Reference Temperature", f"{data.reference_temperature:.1f} °C"),
            ("ROI Source", data.roi_source),
            ("Max Temperature (ROI)", f"{data.maximum_temperature:.1f} °C" if data.maximum_temperature is not None else "-"),
            ("Average Temperature (ROI)", f"{data.mean_temperature:.1f} °C" if data.mean_temperature is not None else "-"),
            ("Loaded Folder", str(self.package.source_path) if self.package and hasattr(self.package,'source_path') else "-"),
        ]
        self.info_window.update_rows(rows)

    def _update_acoustic_cards(self, data):
        trend = getattr(self, "acoustic_control_trend", None)
        if trend is not None:
            self.acoustic_power_curve.setData(np.asarray(trend.time_s,float), np.asarray(trend.power_percent,float), connect="finite")
            self.acoustic_score_curve.setData(np.asarray(trend.time_s,float), np.asarray(trend.score_percent,float), connect="finite")
        self.acoustic_control_cursor.setPos(self._index_to_seconds(self.frame_index,self.current.replay_frame_count) if self.current else 0)
        if trend is None or self.frame_index >= len(trend.power_percent):
            self.acoustic_power_value.setText("Unavailable")
            self.acoustic_score_value.setText("Unavailable")
            self.acoustic_cavitation_value.setText("Unavailable")
            self.acoustic_power_text.setText("Power: --")
            self.acoustic_score_text.setText("Score: --")
            return
        power = trend.power_percent[self.frame_index]
        score = trend.score_percent[self.frame_index]
        energy = trend.energy[self.frame_index]
        limit = trend.harmless_limit[self.frame_index]
        power_text = f"{power:.1f} %" if np.isfinite(power) else "--"
        score_text = f"{score:.1f} %" if np.isfinite(score) else "--"
        self.acoustic_power_value.setText(power_text)
        self.acoustic_score_value.setText(score_text)
        self.acoustic_power_text.setText(f"Power: {power_text}")
        self.acoustic_score_text.setText(f"Score: {score_text}")
        x_max = self._index_to_seconds(max(0, self.current.replay_frame_count - 1), self.current.replay_frame_count) if self.current else 0.0
        self.acoustic_power_text.setPos(x_max, 106.0)
        self.acoustic_score_text.setPos(x_max, 88.0)
        if np.isfinite(energy) and np.isfinite(limit):
            self.acoustic_cavitation_value.setText(f"{energy:.5f} / {limit:.5f}")
        else:
            self.acoustic_cavitation_value.setText("Unavailable")

    def _update_replay_waterfall(self, replay_count: int):
        """Render the true all-bin Time × Frequency spectrogram.

        Coloured overlay lines are selected channels' current-frame FFT curves,
        not peak-frequency or ridge histories. The popup uses this same renderer.
        """
        selected = self._selected_channels()
        source = "Sonication SpectrumMsg"
        result = self.relative_spectrum_renderer.render(
            self.waterfall_replay_plot, self.spectrum_channels, selected,
            self.frame_index, replay_count, self._channel_colors,
            (self.current.main_frequency_hz if self.current else None) or
            (self.package.main_frequency_hz if self.package else None),
            f"Relative Acoustic Spectrum · {source} · {', '.join(selected)}",
        )
        self.waterfall_replay_image = result.image_item

    # ------------------------------------------------------------- Helpers
    def _load_spectrum_channels(self):
        channels = {f"CH{i}": [] for i in range(8)}
        configured = self.sonication_channel_service.read(self.current.folder) if self.current else None
        configured_index = configured.channel if configured and configured.channel is not None else 0
        self._active_spectrum_channel = f"CH{configured_index}"

        son_frames = [] if self.cpc_enabled else self.spectrum_provider.load(list(self.current.spectrum_files), source_kind="Sonication")
        for frame in son_frames:
            explicit = self._channel_name(Path(frame.source), default=None)
            channel = explicit if explicit is not None else self._active_spectrum_channel
            frame.channel = int(channel[2:]); channels[channel].append(frame)

        # CPC mode is a real source switch.  It uses the validated independent
        # 8CH decoder and maps only the CPC file belonging to this sonication.
        if self.cpc_enabled and self.package is not None and self.current is not None:
            replay = self.hydrophone_replay_service.build(
                self.package.cpc_spectrum_files, self.sonication_index, len(self.package.sonications)
            )
            for frame in replay.frames:
                frequency = np.asarray(frame.frequency_hz, dtype=float)
                for channel_index, amplitude in enumerate(frame.channels[:8]):
                    calibrated = np.asarray(amplitude, dtype=float)
                    channels[f"CH{channel_index}"].append(SpectrumFrame(
                        index=frame.index,
                        frequency=[float(v) for v in frequency],
                        amplitude=[float(v) for v in calibrated],
                        timestamp_seconds=frame.index * replay.frame_interval_s,
                        confidence=1.0,
                        source=str(replay.source_fft or "CPC FFT"),
                        channel=channel_index,
                        source_kind="CPCFiles mapped",
                    ))
            if replay.frames:
                son_frames = []

        self.spectrum_channels = channels
        self._rebuild_channel_controls()

    def _rebuild_channel_controls(self):
        previous = set(self.chart_state.selected_channels)
        for action in self.channel_actions.values():
            self.channel_menu.removeAction(action); action.deleteLater()
        self.channel_actions.clear()
        if not self.chart_state.user_selected_channels:
            previous = {self._active_spectrum_channel}
            self.chart_state.selected_channels = set(previous)
        for name in [f"CH{i}" for i in range(8)]:
            action = QAction(name, self.channel_menu)
            action.setCheckable(True); action.setChecked(name in previous)
            action.toggled.connect(self._channel_selection_changed)
            self.channel_actions[name] = action; self.channel_menu.addAction(action)
        self.all_channels_action.blockSignals(True)
        self.all_channels_action.setChecked(len(previous) == 8)
        self.all_channels_action.blockSignals(False)
        self._update_channel_button_text()

    def _cpc_toggled(self, checked: bool):
        self.cpc_enabled = bool(checked); self.chart_state.cpc_enabled = self.cpc_enabled
        self.cpc_button.setText("CPC ON" if checked else "CPC OFF")
        if self.current is not None:
            self._load_spectrum_channels(); self.set_frame(self.frame_index)
        count = len(self.package.cpc_spectrum_files) if self.package is not None else 0
        self.statusBar().showMessage(f"CPCFiles {'enabled' if checked else 'disabled'} ({count} candidate DMP file(s))")

    def _toggle_all_channels(self, checked: bool):
        self.chart_state.user_selected_channels = True
        for action in self.channel_actions.values():
            action.blockSignals(True); action.setChecked(checked); action.blockSignals(False)
        self.chart_state.selected_channels = set(self.channel_actions) if checked else set()
        self._update_channel_button_text(); self.set_frame(self.frame_index)

    def _channel_selection_changed(self):
        self.chart_state.user_selected_channels = True
        selected={name for name,action in self.channel_actions.items() if action.isChecked()}
        self.chart_state.selected_channels=set(selected)
        self.all_channels_action.blockSignals(True)
        self.all_channels_action.setChecked(len(selected)==len(self.channel_actions) and bool(selected))
        self.all_channels_action.blockSignals(False)
        self._update_channel_button_text(); self.set_frame(self.frame_index)

    def _update_channel_button_text(self):
        selected = [name for name, action in self.channel_actions.items() if action.isChecked()]
        if selected and len(selected) == len(self.channel_actions): self.channel_button.setText("CH: All")
        elif len(selected) == 1: self.channel_button.setText(f"CH: {selected[0]}")
        elif selected: self.channel_button.setText(f"CH: {len(selected)}")
        else: self.channel_button.setText("CH: None")

    def _selected_channels(self):
        selected = [name for name, action in self.channel_actions.items() if action.isChecked()]
        return selected or [self._active_spectrum_channel]

    def _hydro_layout_changed(self):
        mode = self.hydro_view.currentText()
        self.analysis_spectrum_plot.setVisible(mode in ("Both", "Spectrum"))
        self.waterfall_plot.setVisible(mode in ("Both", "Waterfall"))
        if mode == "Spectrum":
            self.hydro_splitter.setSizes([1000, 0])
        elif mode == "Waterfall":
            self.hydro_splitter.setSizes([0, 1000])
        else:
            self.hydro_splitter.setSizes([600, 600])
        self._update_analysis_hydrophone()

    def _update_parameter_table(self, data, count: int, spectrum_index, spectrum_count):
        frequency_mhz = ((self.current.main_frequency_hz if self.current else None) or self.package.main_frequency_hz) / 1_000_000.0
        rows = [
            ("Energy", "From ACT when available", "Sonication", self.current.name),
            ("Power", "From ACT when available", "Replay Frame", f"{self.frame_index + 1}/{count}"),
            ("Duration", f"{self._index_to_seconds(count - 1, count):.1f} sec", "Temperature RAW", f"{data.temperature_index + 1 if data.temperature_index is not None else '-'}"),
            ("Frequency", f"{frequency_mhz:.3f} MHz", "SpectrumMsg", f"{spectrum_index + 1 if spectrum_index is not None else '-'}/{spectrum_count or '-'}"),
            ("Temperature Source", data.temperature_source, "Max Temperature (ROI)", f"{data.maximum_temperature:.1f} °C" if data.maximum_temperature is not None else "-"),
            ("Reference Temperature", f"{data.reference_temperature:.1f} °C", "Average Temperature (ROI)", f"{data.mean_temperature:.1f} °C" if data.mean_temperature is not None else "-"),
            ("ROI Source", data.roi_source, "Max ΔTemperature", f"{data.maximum_delta_temperature:.1f} °C" if data.maximum_delta_temperature is not None else "-"),
        ]
        self.parameter_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                self.parameter_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

    def _add_spectrum_reference_lines(self, plot, mhz: bool):
        if not self.package:
            return
        divisor = 1_000_000.0 if mhz else 1000.0
        main = self.package.main_frequency_hz / divisor
        for frequency, label in ((main / 2, "Sub"), (main, "Main"), (main * 2, "2nd"), (main * 3, "3rd")):
            plot.addItem(pg.InfiniteLine(pos=frequency, angle=90, movable=False, label=label))

    def _current_temperature_range(self):
        levels=self._temperature_levels(None)
        return levels if levels is not None else (40.0,60.0)

    def _temperature_range_changed(self, _index):
        lo,hi=self._current_temperature_range()
        self.temperature_plot.setYRange(lo,hi,padding=0)
        self.settings.setValue("temperature_range", self.range_combo.currentText())
        self.set_frame(self.frame_index)

    def _capture_overlay_state_debounced(self):
        if hasattr(self,"_overlay_save_timer"):
            self._overlay_save_timer.start(120)

    def _save_overlay_state(self):
        if hasattr(self,"overlay") and self._restore_overlay_session:
            self._overlay_session_view = self.overlay.view_range()

    def _capture_overlay_levels(self, low, high):
        if self._restore_overlay_session:
            self._overlay_session_levels = (float(low), float(high))

    @staticmethod
    def _amplitude_db(values):
        amplitude=np.abs(np.nan_to_num(np.asarray(values,float),nan=0.0,posinf=0.0,neginf=0.0))
        if amplitude.size == 0:
            return amplitude
        reference=max(float(np.nanmax(amplitude)),1e-30)
        return np.clip(20.0*np.log10(np.maximum(amplitude,reference*1e-5)/reference),-100.0,0.0)

    @staticmethod
    def _relative_spectrum(values):
        """Scale one spectrum onto the workstation-like 0..4 relative axis."""
        amplitude = np.abs(np.nan_to_num(np.asarray(values, float), nan=0.0, posinf=0.0, neginf=0.0))
        if amplitude.size == 0:
            return amplitude
        baseline = float(np.percentile(amplitude, 10))
        signal = np.maximum(amplitude - baseline, 0.0)
        reference = float(np.percentile(signal, 99.5))
        if not np.isfinite(reference) or reference <= 1e-30:
            reference = max(float(np.nanmax(signal)), 1e-30)
        normalized = signal / reference
        # Keep quiet frames slightly above zero so the noise floor is visible,
        # while cavitation peaks retain enough headroom to stand out clearly.
        return np.clip(0.08 + normalized * 7.2, 0.0, 8.0)

    def _temperature_lut_with_red_threshold(self, low: float, high: float):
        """Keep all temperature colors visible and move the red transition only."""
        low, high = float(low), float(high)
        if high <= low:
            high = low + 1.0
        red = float(np.clip(self.threshold_slider.value(), low, high))
        split = float(np.clip((red - low) / (high - low), 0.02, 0.98))
        positions = np.asarray([0.0, max(0.0, split * 0.55), max(0.0, split * 0.85), split, 1.0], float)
        positions = np.maximum.accumulate(positions)
        colors = np.asarray([
            (0, 0, 0, 0),
            (255, 235, 45, 180),
            (255, 145, 20, 215),
            (255, 0, 0, 240),
            (255, 0, 0, 255),
        ], dtype=np.ubyte)
        cmap = pg.ColorMap(positions, colors)
        return cmap.getLookupTable(0.0, 1.0, 256)

    def _temperature_mode_changed(self, text: str):
        self.temperature_display_mode = text
        self.range_combo.setEnabled(not text.startswith("Δ"))
        self.threshold_slider.setEnabled(not text.startswith("Δ"))
        self.set_frame(self.frame_index)

    def _temperature_levels(self, temperature):
        index = self.range_combo.currentIndex()
        if index == 0:
            return 40.0, 60.0
        if index == 1:
            return 35.0, 60.0
        if index == 2:
            return 30.0, 90.0
        if index == 3:
            return 0.0, 60.0
        finite = temperature[np.isfinite(temperature)] if temperature is not None else np.array([])
        if not finite.size:
            return None
        lo, hi = np.percentile(finite, [1, 99.5])
        return float(lo), max(float(lo) + 1.0, float(hi))

    def _delta_levels(self, delta):
        finite = delta[np.isfinite(delta)] if delta is not None else np.array([])
        return (0.0, max(1.0, float(np.percentile(finite, 99)))) if finite.size else None

    @staticmethod
    def _channel_name(path: Path, default: str | None = "CH0") -> str | None:
        text = f"{path.parent.name}_{path.stem}"
        for pattern in (r"(?:^|[_\- ])(?:CH|HP)[_\- ]?(\d+)", r"hydrophone[_\- ]?(\d+)"):
            match = re.search(pattern, text, re.I)
            if match:
                return f"CH{int(match.group(1))}"
        return default

    @staticmethod
    def _map_replay_to_data(index: int, replay_count: int, data_count: int) -> int:
        """Map one replay position to another stream with endpoint-safe ratio.

        This is the explicit fallback when timestamps are absent. It guarantees
        frame movement changes Spectrum/Waterfall position instead of leaving a
        static first record.
        """
        if data_count <= 1 or replay_count <= 1:
            return 0
        ratio = index / float(replay_count - 1)
        return max(0, min(data_count - 1, int(round(ratio * (data_count - 1)))))

    @staticmethod
    def _map_data_to_replay(index: int, data_count: int, replay_count: int) -> int:
        """Inverse endpoint-safe mapping used by thumbnail selection."""
        if replay_count <= 1 or data_count <= 1:
            return 0
        ratio = max(0, min(data_count - 1, int(index))) / float(data_count - 1)
        return max(0, min(replay_count - 1, int(round(ratio * (replay_count - 1)))))


    def _index_to_seconds(self, index: int, count: int) -> float:
        if count <= 1:
            return 0.0
        duration = float(getattr(self, "current_timeline_duration_s", 0.0) or 0.0)
        if duration <= 0:
            duration = float(count - 1)
        ratio = max(0.0, min(1.0, float(index) / float(count - 1)))
        return ratio * duration

    def _replay_duration_s(self) -> float:
        """Return the active replay duration without assuming metadata exists."""
        count = int(getattr(self.current, "replay_frame_count", 0) or 0) if self.current else 0
        duration = float(getattr(self, "current_timeline_duration_s", 0.0) or 0.0)
        if duration > 0.0:
            return duration
        return float(max(0, count - 1))

    def _seconds_to_index(self, seconds: float, count: int) -> int:
        """Map a chart time back to a replay index, clamped to valid bounds."""
        count = max(1, int(count or 1))
        if count <= 1:
            return 0
        duration = self._replay_duration_s()
        if duration <= 0.0:
            return max(0, min(count - 1, int(round(float(seconds)))))
        ratio = max(0.0, min(1.0, float(seconds) / duration))
        return max(0, min(count - 1, int(round(ratio * (count - 1)))))

    def _frame_time_axis(self, count: int):
        return np.asarray([self._index_to_seconds(index, count) for index in range(count)], float)

    @staticmethod
    def _array_icon(array):
        if array is None:
            return QIcon()
        values = np.nan_to_num(np.asarray(array, float))
        low, high = np.percentile(values, [2, 98]) if values.size else (0, 1)
        if high <= low:
            high = low + 1
        gray = np.clip((values - low) / (high - low) * 255, 0, 255).astype(np.uint8)
        rgb = np.stack([gray, gray, gray], axis=2)
        height, width = rgb.shape[:2]
        image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
        return QIcon(QPixmap.fromImage(image).scaled(110, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _open_chart_popup(self,key: str):
        popup=ChartPopup({"temperature":"Temperature Trend (ROI)","spectrum":"Acoustic Spectrum","acoustic":"Power % / Score","waterfall":"Relative Acoustic Spectrum (disabled)"}.get(key,key),self)
        if not hasattr(self,"_chart_popups"): self._chart_popups=[]
        popup.chart_key=key; self._chart_popups.append(popup)
        self._render_chart_popup(popup)
        popup.show(); popup.raise_()

    def _render_chart_popup(self,popup):
        key=getattr(popup,"chart_key",""); plot=popup.plot; plot.clear(); popup.hover_text=pg.TextItem(anchor=(0,1),color="#ffffff",fill=pg.mkBrush(0,0,0,210)); popup.hover_text.setZValue(100); popup.hover_text.hide(); plot.addItem(popup.hover_text)
        popup.hover_series=[]
        if key=="temperature":
            x=self._frame_time_axis(len(self.max_temperature_trend)); lo,hi=self._temperature_data_range(); plot.setYRange(lo,hi,padding=0.05); plot.setLabel("left","Temperature",units="°C"); plot.setLabel("bottom","Replay time",units="sec")
            if len(x): plot.setXRange(float(x[0]), float(x[-1]), padding=0.02)
            plot.plot(x,self.max_temperature_trend,pen=pg.mkPen("#ff3b30",width=3),connect="finite"); plot.plot(x,self.mean_temperature_trend,pen=pg.mkPen("#49e36b",width=2.5),connect="finite")
            if self.cursor_temperature_trend: plot.plot(x,self.cursor_temperature_trend,pen=pg.mkPen("#b98cff",width=1.6,style=Qt.PenStyle.DashLine))
            plot.addLine(x=self._index_to_seconds(self.frame_index,len(x)),pen=pg.mkPen("#00bfff",width=1.3))
            popup.set_hover_series([("Max",x,self.max_temperature_trend," °C"),("ROI Avg",x,self.mean_temperature_trend," °C"),("Cursor",x,self.cursor_temperature_trend," °C")])
        elif key=="acoustic":
            trend=getattr(self,"acoustic_control_trend",None); plot.setYRange(0,110,padding=0); plot.setLabel("left","Power / Score",units="%"); plot.setLabel("bottom","Replay time",units="sec")
            if trend is not None:
                plot.plot(trend.time_s,trend.power_percent,pen=pg.mkPen("#58f26a",width=2.5),connect="finite"); plot.plot(trend.time_s,trend.score_percent,pen=pg.mkPen("#ff9d22",width=2.5),connect="finite"); plot.addLine(x=self._index_to_seconds(self.frame_index,self.current.replay_frame_count),pen=pg.mkPen("#00bfff",width=1.3))
                popup.set_hover_series([("Power",trend.time_s,trend.power_percent," %"),("Score",trend.time_s,trend.score_percent," %")])
        elif key=="spectrum":
            selected=self._selected_channels()
            replay_count=self.current.replay_frame_count if self.current else 1
            main_frequency=((self.current.main_frequency_hz if self.current else None) or
                            (self.package.main_frequency_hz if self.package else None))
            result=self.current_spectrum_renderer.render(
                plot, self.spectrum_channels, selected, self.frame_index,
                replay_count, self._channel_colors, main_frequency,
                self._map_replay_to_data,
                self._index_to_seconds(self.frame_index,replay_count),
                mode=self.chart_state.spectrum_mode,
                average_window=self.chart_state.spectrum_average_window,
            )
            plot.addItem(popup.hover_text)
            saved_x=self.chart_state.x_ranges.get("spectrum")
            saved_y=self.chart_state.y_ranges.get("spectrum")
            if saved_x is not None: plot.setXRange(*saved_x,padding=0)
            if saved_y is not None: plot.setYRange(*saved_y,padding=0)
            popup.set_hover_series(result.series)
        elif key=="waterfall":
            self._render_waterfall_popup(plot)

    def _render_waterfall_popup(self,plot):
        selected=self._selected_channels()
        source="Sonication SpectrumMsg"
        self.relative_spectrum_renderer.render(
            plot, self.spectrum_channels, selected, self.frame_index,
            self.current.replay_frame_count if self.current else 1,
            self._channel_colors,
            (self.current.main_frequency_hz if self.current else None) or
            (self.package.main_frequency_hz if self.package else None),
            f"Relative Acoustic Spectrum · {source} · {', '.join(selected)}",
        )

    def _refresh_chart_popups(self):
        for popup in list(getattr(self,"_chart_popups",[])):
            if popup.isVisible(): self._render_chart_popup(popup)

    # -------------------------------------------------------------- Controls
    def _spectrum_mode_changed(self, text: str) -> None:
        self.chart_state.spectrum_mode = text or "Average"
        if self.current:
            self.set_frame(self.frame_index)

    def _temperature_data_range(self) -> tuple[float, float]:
        arrays = [self.max_temperature_trend, self.mean_temperature_trend, self.cursor_temperature_trend]
        finite = []
        for values in arrays:
            arr = np.asarray(values, float)
            if arr.size:
                finite.append(arr[np.isfinite(arr)])
        finite = [v for v in finite if v.size]
        if not finite:
            return self._current_temperature_range()
        values = np.concatenate(finite)
        low = float(np.nanmin(values)); high = float(np.nanmax(values))
        pad = max(1.0, (high-low)*0.10)
        return low-pad, high+pad

    def _fit_temperature_trend(self, force: bool = False) -> None:
        if not self.current or (self.chart_state.temperature_user_zoomed and not force):
            return
        x = self._frame_time_axis(self.current.replay_frame_count)
        if not len(x):
            return
        lo, hi = self._temperature_data_range()
        self._updating_temperature_range = True
        try:
            self.temperature_plot.setXRange(float(x[0]), float(x[-1]), padding=0.02)
            self.temperature_plot.setYRange(lo, hi, padding=0.02)
        finally:
            self._updating_temperature_range = False

    def _temperature_range_changed_by_user(self, *_args) -> None:
        if self._updating_temperature_range:
            return
        self.chart_state.temperature_user_zoomed = True
        try:
            xr, yr = self.temperature_plot.plotItem.vb.viewRange()
            self.chart_state.remember_range("temperature", xr, yr)
        except Exception:
            pass

    def _remember_chart_range(self, key: str, plot) -> None:
        try:
            x_range, y_range = plot.plotItem.vb.viewRange()
            self.chart_state.remember_range(key, x_range, y_range)
        except Exception:
            return

    def _spectrum_plot_hovered(self, event):
        scene_pos = event[0] if isinstance(event, (tuple, list)) else event
        if not self.spectrum_hover_series or not self.spectrum_plot.sceneBoundingRect().contains(scene_pos):
            self.spectrum_hover_text.hide(); return
        point = self.spectrum_plot.plotItem.vb.mapSceneToView(scene_pos)
        lines = [f"Frequency: {point.x():.4f} MHz"]
        best_y = None
        for label, x_values, y_values, _unit in self.spectrum_hover_series:
            x=np.asarray(x_values,float); y=np.asarray(y_values,float)
            valid=np.isfinite(x)&np.isfinite(y)
            if not valid.any(): continue
            xv=x[valid]; yv=y[valid]; i=int(np.argmin(np.abs(xv-point.x())))
            value=float(yv[i]); lines.append(f"{label}: {value:.3f}")
            if best_y is None: best_y=value
        if best_y is None:
            self.spectrum_hover_text.hide(); return
        self.spectrum_hover_text.setText("\n".join(lines))
        self.spectrum_hover_text.setPos(point.x(), best_y)
        self.spectrum_hover_text.show()

    def _acoustic_plot_hovered(self, event):
        scene_pos=event[0] if isinstance(event,(tuple,list)) else event
        trend=getattr(self,"acoustic_control_trend",None)
        if trend is None or not self.acoustic_control_plot.sceneBoundingRect().contains(scene_pos):
            self.acoustic_hover_text.hide(); return
        point=self.acoustic_control_plot.plotItem.vb.mapSceneToView(scene_pos)
        x=np.asarray(trend.time_s,float)
        if not x.size: self.acoustic_hover_text.hide(); return
        i=int(np.argmin(np.abs(x-point.x())))
        lines=[f"{x[i]:.2f} sec"]
        if i < len(trend.power_percent) and np.isfinite(trend.power_percent[i]): lines.append(f"Power: {trend.power_percent[i]:.1f} %")
        if i < len(trend.score_percent) and np.isfinite(trend.score_percent[i]): lines.append(f"Score: {trend.score_percent[i]:.1f} %")
        self.acoustic_hover_text.setText("\n".join(lines)); self.acoustic_hover_text.setPos(point.x(),point.y()); self.acoustic_hover_text.show()

    def _temperature_plot_clicked(self, event):
        if not self.current:
            return
        point = self.temperature_plot.plotItem.vb.mapSceneToView(event.scenePos())
        self.set_frame(self._seconds_to_index(point.x(), self.current.replay_frame_count))

    def _temperature_plot_hovered(self, event):
        if not self.current or not self.max_temperature_trend:
            self.temperature_hover_text.hide(); return
        scene_pos = event[0] if isinstance(event, (tuple, list)) else event
        if not self.temperature_plot.sceneBoundingRect().contains(scene_pos):
            self.temperature_hover_text.hide(); return
        point = self.temperature_plot.plotItem.vb.mapSceneToView(scene_pos)
        index = self._seconds_to_index(point.x(), len(self.max_temperature_trend))
        max_t = self.max_temperature_trend[index]
        avg_t = self.mean_temperature_trend[index] if index < len(self.mean_temperature_trend) else np.nan
        cursor_t = self.cursor_temperature_trend[index] if index < len(self.cursor_temperature_trend) else np.nan
        lines = [f"{self._index_to_seconds(index, len(self.max_temperature_trend)):.1f} sec"]
        if np.isfinite(max_t): lines.append(f"Max {max_t:.1f} °C")
        if np.isfinite(avg_t): lines.append(f"Avg {avg_t:.1f} °C")
        if np.isfinite(cursor_t): lines.append(f"Cursor {cursor_t:.1f} °C")
        self.temperature_hover_text.setText("\n".join(lines))
        self.temperature_hover_text.setPos(point.x(), point.y())
        self.temperature_hover_text.show()

    def _acoustic_plot_clicked(self, event):
        if not self.current:
            return
        point = self.acoustic_control_plot.plotItem.vb.mapSceneToView(event.scenePos())
        self.set_frame(self._seconds_to_index(point.x(), self.current.replay_frame_count))

    def slider_changed(self, value):
        self._activate_replay_mode_for_navigation()
        self.set_frame(value)

    def previous_frame(self):
        if not self.current:
            return
        self._activate_replay_mode_for_navigation()
        self.set_frame(self.frame_index - 1)

    def next_frame(self):
        if not self.current:
            return
        self._activate_replay_mode_for_navigation()
        current = self.frame_index
        count = max(1, self.current.replay_frame_count)
        target = current + 1
        if target >= count:
            if self.timer.isActive() and getattr(self, "workstation_replay_enabled", True):
                self.timer.stop()
                self.play_btn.setText("▶")
                target = count - 1
            elif self.timer.isActive():
                target = 0
            else:
                target = count - 1
        self.set_frame(target)

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText("▶")
        else:
            self.timer.start(max(20, int(1000 / self.speed.value())))
            self.play_btn.setText("Ⅱ")

    def speed_changed(self, value):
        if self.timer.isActive():
            self.timer.start(max(20, int(1000 / value)))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.previous_frame()
            return
        if event.key() == Qt.Key.Key_Right:
            self.next_frame()
            return
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if self.current:
            self._activate_replay_mode_for_navigation()
            delta = 1 if event.angleDelta().y() < 0 else -1
            self.set_frame(self.frame_index + delta)
            event.accept()
            return
        super().wheelEvent(event)

    def dragEnterEvent(self, event):
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_dir() or path.suffix.lower() == ".zip":
                    self.load(path)
                    event.acceptProposedAction()
                    break

    def _restore(self):
        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
            layout_version = int(self.settings.value("layout/version", 0) or 0)
            for key, splitter in (("top_split", getattr(self,"top_split",None)),("graph_split",getattr(self,"graph_split",None)),("lower_split",getattr(self,"lower_split",None))):
                # Do not restore the pre-C0046 graph ratio, which encoded the
                # incorrect 3:4 temperature/spectrum split.
                if key == "graph_split" and layout_version < 46:
                    continue
                state=self.settings.value(key)
                if state and splitter is not None: splitter.restoreState(state)
            if getattr(self, "graph_split", None) is not None and layout_version < 46:
                self.graph_split.setSizes([650, 350])
            saved_range=self.settings.value("temperature_range", "40–60 °C")
            self.chart_state.cpc_enabled = str(self.settings.value("chart/cpc_enabled", "false")).lower() == "true"
            self.cpc_enabled = False
            self.chart_state.cpc_enabled = False
            saved_channels = self.settings.value("chart/selected_channels", []) or []
            if isinstance(saved_channels, str): saved_channels=[saved_channels]
            self.chart_state.selected_channels=set(map(str,saved_channels))
            self.chart_state.user_selected_channels=bool(saved_channels)
            self.cpc_button.blockSignals(True); self.cpc_button.setChecked(self.cpc_enabled); self.cpc_button.setText("CPC ON" if self.cpc_enabled else "CPC OFF"); self.cpc_button.blockSignals(False)
            idx=self.range_combo.findText(str(saved_range)); self.range_combo.setCurrentIndex(idx if idx>=0 else 0)
        except Exception:
            pass

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        for key, splitter in (("top_split", getattr(self,"top_split",None)),("graph_split",getattr(self,"graph_split",None)),("lower_split",getattr(self,"lower_split",None))):
            if splitter is not None: self.settings.setValue(key, splitter.saveState())
        self.settings.setValue("layout/version", 46)
        self.settings.setValue("chart/cpc_enabled", self.cpc_enabled)
        self.settings.setValue("chart/selected_channels", sorted(self.chart_state.selected_channels))
        super().closeEvent(event)
