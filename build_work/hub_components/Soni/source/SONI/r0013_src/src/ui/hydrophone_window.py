from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QSlider, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from src.services.hydrophone_replay_service import HydrophoneReplayService, CpcHydrophoneReplay


class EightHydrophoneWindow(QDialog):
    sonicationRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CPC Spectrum / 8CH Hydrophone Analyzer — RC1-C0045")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.resize(1500, 930)
        self.service = HydrophoneReplayService()
        self.package = None
        self.replay: CpcHydrophoneReplay | None = None
        self.frame_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.set_frame(self.frame_index + 1))

        top = QHBoxLayout()
        self.sonication_combo = QComboBox()
        self.sonication_combo.currentIndexChanged.connect(self._sonication_changed)
        self.channel_spin = QSpinBox(); self.channel_spin.setRange(0, 7)
        self.channel_spin.valueChanged.connect(self._refresh_all)
        self.source_label = QLabel("No CPC source loaded")
        self.source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top.addWidget(QLabel("Sonication")); top.addWidget(self.sonication_combo)
        top.addWidget(QLabel("Analysis CH")); top.addWidget(self.channel_spin)
        top.addWidget(self.source_label, 1)

        self.note = QLabel("No data")
        self.note.setWordWrap(True)

        self.tabs = QTabWidget()
        self.raw_tab = self._build_raw_tab()
        self.spectrum_tab = self._build_spectrum_tab()
        self.spectrogram_tab = self._build_spectrogram_tab()
        self.band_tab = self._build_band_tab()
        self.navigator_tab = self._build_navigator_tab()
        self.tabs.addTab(self.raw_tab, "Measurement Timeline / Raw A/D")
        self.tabs.addTab(self.spectrum_tab, "Spectrum")
        self.tabs.addTab(self.spectrogram_tab, "Spectrogram")
        self.tabs.addTab(self.band_tab, "Band Energy")
        self.tabs.addTab(self.navigator_tab, "Measure / Statistics")

        controls = QHBoxLayout()
        self.first_btn = QPushButton("|◀")
        self.prev_btn = QPushButton("◀")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("▶")
        self.last_btn = QPushButton("▶|")
        self.first_btn.clicked.connect(lambda: self.set_frame(0))
        self.prev_btn.clicked.connect(lambda: self.set_frame(self.frame_index - 1))
        self.next_btn.clicked.connect(lambda: self.set_frame(self.frame_index + 1))
        self.last_btn.clicked.connect(lambda: self.set_frame(len(self.replay.frames)-1 if self.replay else 0))
        self.play_btn.clicked.connect(self._toggle_play)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self.set_frame)
        self.measure_spin = QSpinBox(); self.measure_spin.setRange(1, 1)
        self.measure_spin.valueChanged.connect(lambda v: self.set_frame(v - 1))
        self.frame_label = QLabel("Measure - / - · Time -")
        controls.addWidget(self.first_btn); controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn); controls.addWidget(self.next_btn); controls.addWidget(self.last_btn)
        controls.addWidget(self.slider, 1)
        controls.addWidget(QLabel("Measure #")); controls.addWidget(self.measure_spin)
        controls.addWidget(self.frame_label)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.note)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(controls)

    def _plot(self, bottom: str, left: str) -> pg.PlotWidget:
        plot = pg.PlotWidget()
        plot.showGrid(x=True, y=True, alpha=.25)
        plot.setLabel("bottom", bottom)
        plot.setLabel("left", left)
        return plot

    def _build_raw_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.raw_mode = QComboBox(); self.raw_mode.addItems(["Overlay 8CH", "Single CH", "8 Panels"])
        self.raw_mode.currentIndexChanged.connect(self._rebuild_raw_plots)
        self.raw_scale = QComboBox(); self.raw_scale.addItems(["Auto", "Common symmetric"])
        self.raw_scale.currentIndexChanged.connect(self._draw_raw)
        row.addWidget(QLabel("Display")); row.addWidget(self.raw_mode)
        row.addWidget(QLabel("Y scale")); row.addWidget(self.raw_scale); row.addStretch(1)
        layout.addLayout(row)
        self.raw_host = QWidget(); self.raw_layout = QGridLayout(self.raw_host); self.raw_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.raw_host, 1)
        self.raw_plots: list[pg.PlotWidget] = []
        self._rebuild_raw_plots()
        return page

    def _build_spectrum_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.spectrum_mode = QComboBox(); self.spectrum_mode.addItems(["Overlay 8CH", "Single CH", "8 Panels"])
        self.spectrum_mode.currentIndexChanged.connect(self._rebuild_spectrum_plots)
        self.db_floor = QSpinBox(); self.db_floor.setRange(-120, -20); self.db_floor.setValue(-60)
        self.db_floor.valueChanged.connect(self._draw_spectrum)
        row.addWidget(QLabel("Display")); row.addWidget(self.spectrum_mode)
        row.addWidget(QLabel("Floor")); row.addWidget(self.db_floor); row.addWidget(QLabel("dB")); row.addStretch(1)
        layout.addLayout(row)
        self.spectrum_host = QWidget(); self.spectrum_layout = QGridLayout(self.spectrum_host); self.spectrum_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.spectrum_host, 1)
        self.spectrum_plots: list[pg.PlotWidget] = []
        self._rebuild_spectrum_plots()
        return page

    def _build_spectrogram_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.spec_min = QDoubleSpinBox(); self.spec_min.setRange(0.0, 10.0); self.spec_min.setDecimals(3); self.spec_min.setValue(0.20); self.spec_min.setSuffix(" MHz")
        self.spec_max = QDoubleSpinBox(); self.spec_max.setRange(0.0, 10.0); self.spec_max.setDecimals(3); self.spec_max.setValue(1.00); self.spec_max.setSuffix(" MHz")
        self.spec_min.valueChanged.connect(self._draw_spectrogram); self.spec_max.valueChanged.connect(self._draw_spectrogram)
        row.addWidget(QLabel("Frequency range")); row.addWidget(self.spec_min); row.addWidget(QLabel("to")); row.addWidget(self.spec_max); row.addStretch(1)
        layout.addLayout(row)
        self.spectrogram_plot = pg.PlotWidget()
        self.spectrogram_plot.setLabel("bottom", "Time", "s")
        self.spectrogram_plot.setLabel("left", "Frequency", "MHz")
        self.spectrogram_image = pg.ImageItem(axisOrder="row-major")
        self.spectrogram_plot.addItem(self.spectrogram_image)
        self.spectrogram_plot.setMouseEnabled(x=True, y=True)
        layout.addWidget(self.spectrogram_plot, 1)
        return page

    def _build_band_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        controls = QGridLayout()
        self.band_enabled: list[QCheckBox] = []
        self.band_low: list[QDoubleSpinBox] = []
        self.band_high: list[QDoubleSpinBox] = []
        for i, (low, high) in enumerate(self.service.DEFAULT_BANDS_MHZ):
            enabled = QCheckBox(f"Band {i}"); enabled.setChecked(i == 0)
            lo = QDoubleSpinBox(); lo.setRange(0.0, 10.0); lo.setDecimals(3); lo.setValue(low); lo.setSuffix(" MHz")
            hi = QDoubleSpinBox(); hi.setRange(0.0, 10.0); hi.setDecimals(3); hi.setValue(high); hi.setSuffix(" MHz")
            enabled.toggled.connect(self._draw_band_energy); lo.valueChanged.connect(self._draw_band_energy); hi.valueChanged.connect(self._draw_band_energy)
            controls.addWidget(enabled, i//3, (i%3)*3)
            controls.addWidget(lo, i//3, (i%3)*3+1)
            controls.addWidget(hi, i//3, (i%3)*3+2)
            self.band_enabled.append(enabled); self.band_low.append(lo); self.band_high.append(hi)
        layout.addLayout(controls)
        self.band_plot = self._plot("Time (s)", "Relative band energy (dB)")
        layout.addWidget(self.band_plot, 1)
        return page

    def _build_navigator_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        self.packet_label = QLabel("No measure selected")
        layout.addWidget(self.packet_label)
        self.stats_table = QTableWidget(8, 6)
        self.stats_table.setHorizontalHeaderLabels(["CH", "Raw peak", "Raw RMS", "Dominant MHz", "Peak dB", "Band energy"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        layout.addWidget(self.stats_table, 1)
        return page

    def _clear_layout(self, layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()

    def _rebuild_raw_plots(self) -> None:
        if not hasattr(self, "raw_layout"): return
        self._clear_layout(self.raw_layout); self.raw_plots = []
        mode = self.raw_mode.currentText()
        count = 8 if mode == "8 Panels" else 1
        for i in range(count):
            plot = self._plot("Measurement time (s)", "History value")
            if count == 8:
                plot.setTitle(f"CH{i}"); self.raw_layout.addWidget(plot, i//4, i%4)
            else:
                self.raw_layout.addWidget(plot, 0, 0)
            self.raw_plots.append(plot)
        self._draw_raw()

    def _rebuild_spectrum_plots(self) -> None:
        if not hasattr(self, "spectrum_layout"): return
        self._clear_layout(self.spectrum_layout); self.spectrum_plots = []
        mode = self.spectrum_mode.currentText()
        count = 8 if mode == "8 Panels" else 1
        for i in range(count):
            plot = self._plot("Frequency (MHz)", "Relative level (dB)")
            plot.setXRange(0.0, 1.0, padding=0.0)
            if count == 8:
                plot.setTitle(f"CH{i}"); self.spectrum_layout.addWidget(plot, i//4, i%4)
            else:
                self.spectrum_layout.addWidget(plot, 0, 0)
            self.spectrum_plots.append(plot)
        self._draw_spectrum()

    def load_package(self, package, sonication_index: int):
        self.package = package
        self.sonication_combo.blockSignals(True); self.sonication_combo.clear()
        for i, son in enumerate(package.sonications): self.sonication_combo.addItem(son.name, i)
        self.sonication_combo.setCurrentIndex(max(0, sonication_index)); self.sonication_combo.blockSignals(False)
        self.load_sonication(sonication_index)

    def load_sonication(self, index: int):
        if self.package is None: return
        self.replay = self.service.build(self.package.cpc_spectrum_files, index, len(self.package.sonications))
        fft = self.replay.source_fft.name if self.replay.source_fft else "No FFT"
        raw = self.replay.source_raw.name if self.replay.source_raw else "No raw"
        self.source_label.setText(f"FFT: {fft} | RAW: {raw}")
        self.note.setText(self.replay.note)
        count = len(self.replay.frames)
        self.slider.setRange(0, max(0, count-1))
        self.measure_spin.setRange(1, max(1, count))
        self.set_frame(0)
        self._draw_spectrogram(); self._draw_band_energy()

    def sync_sonication(self, index: int):
        if self.sonication_combo.count() and self.sonication_combo.currentIndex() != index:
            self.sonication_combo.blockSignals(True); self.sonication_combo.setCurrentIndex(index); self.sonication_combo.blockSignals(False)
        self.load_sonication(index)

    def _sonication_changed(self, index: int):
        if index < 0: return
        self.load_sonication(index); self.sonicationRequested.emit(index)

    def set_frame(self, index: int):
        count = len(self.replay.frames) if self.replay else 0
        self.frame_index = max(0, min(int(index), max(0, count-1)))
        self.slider.blockSignals(True); self.slider.setValue(self.frame_index); self.slider.blockSignals(False)
        self.measure_spin.blockSignals(True); self.measure_spin.setValue(self.frame_index+1); self.measure_spin.blockSignals(False)
        interval = self.replay.frame_interval_s if self.replay else 0.010
        self.frame_label.setText(f"FFT Snapshot {self.frame_index+1 if count else '-'} / {count or '-'} · Time {self.frame_index*interval:.3f} s")
        if self.timer.isActive() and count and self.frame_index >= count-1:
            self.timer.stop(); self.play_btn.setText("▶")
        self._refresh_frame_views()

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop(); self.play_btn.setText("▶")
        else:
            if self.replay and self.replay.frames and self.frame_index >= len(self.replay.frames)-1: self.set_frame(0)
            interval = self.replay.frame_interval_s if self.replay else 0.010
            self.timer.start(max(10, int(interval*1000))); self.play_btn.setText("Ⅱ")

    def _refresh_all(self):
        self._refresh_frame_views(); self._draw_spectrogram(); self._draw_band_energy()

    def _refresh_frame_views(self):
        self._draw_raw(); self._draw_spectrum(); self._draw_statistics()

    def _draw_raw(self):
        for plot in getattr(self, "raw_plots", []): plot.clear()
        if not self.replay or not self.replay.frames or not self.raw_plots: return
        frame = self.replay.frames[self.frame_index]
        if not frame.raw_channels:
            if self.replay.raw_timeline_channels:
                t = self.replay.raw_timeline_time_s
                mode = self.raw_mode.currentText()
                channels = range(8) if mode != "Single CH" else [self.channel_spin.value()]
                if mode == "8 Panels":
                    for ch, plot in enumerate(self.raw_plots):
                        y = self.replay.raw_timeline_channels[ch]
                        plot.plot(t[:len(y)], y, pen=pg.intColor(ch, 8))
                        plot.setLabel("bottom", "Measurement time", units="s")
                        plot.setLabel("left", "History value")
                        plot.setTitle(f"CH{ch} measurement history")
                else:
                    plot = self.raw_plots[0]
                    for ch in channels:
                        y = self.replay.raw_timeline_channels[ch]
                        plot.plot(t[:len(y)], y, pen=pg.intColor(ch, 8), name=f"CH{ch}")
                    plot.setLabel("bottom", "Measurement time", units="s")
                    plot.setLabel("left", "History value")
                    suffix = "Raw A/D payload is not present in this export"
                    plot.setTitle(f"Validated CPC 8CH measurement history — {suffix}")
            else:
                self.raw_plots[0].setTitle("CPC raw companion container not decoded")
            return
        mode = self.raw_mode.currentText()
        channels = range(8) if mode != "Single CH" else [self.channel_spin.value()]
        common = max((float(np.max(np.abs(frame.raw_channels[ch]))) for ch in channels if len(frame.raw_channels[ch])), default=1.0)
        if mode == "8 Panels":
            for ch, plot in enumerate(self.raw_plots):
                y = frame.raw_channels[ch]; plot.plot(np.arange(len(y)), y, pen=pg.intColor(ch, 8))
                if self.raw_scale.currentText() == "Common symmetric": plot.setYRange(-common, common, padding=.02)
        else:
            plot = self.raw_plots[0]
            for ch in channels:
                y = frame.raw_channels[ch]; plot.plot(np.arange(len(y)), y, pen=pg.intColor(ch, 8), name=f"CH{ch}")
            plot.setTitle("CH0–CH7 raw overlay" if mode == "Overlay 8CH" else f"CH{self.channel_spin.value()} raw")
            if self.raw_scale.currentText() == "Common symmetric": plot.setYRange(-common, common, padding=.02)

    def _draw_spectrum(self):
        for plot in getattr(self, "spectrum_plots", []): plot.clear()
        if not self.replay or not self.replay.frames or not self.spectrum_plots: return
        frame = self.replay.frames[self.frame_index]; x = frame.frequency_hz / 1e6
        floor = float(self.db_floor.value())
        mode = self.spectrum_mode.currentText()
        channels = range(8) if mode != "Single CH" else [self.channel_spin.value()]
        if mode == "8 Panels":
            for ch, plot in enumerate(self.spectrum_plots):
                y = self.service.relative_db(self.replay, frame, ch)
                plot.plot(x, np.maximum(y, floor), pen=pg.intColor(ch, 8)); plot.setYRange(floor, 0.0, padding=0.0)
        else:
            plot = self.spectrum_plots[0]
            for ch in channels:
                y = self.service.relative_db(self.replay, frame, ch)
                plot.plot(x, np.maximum(y, floor), pen=pg.intColor(ch, 8), name=f"CH{ch}")
            plot.setTitle("CH0–CH7 spectrum overlay" if mode == "Overlay 8CH" else f"CH{self.channel_spin.value()} spectrum")
            plot.setYRange(floor, 0.0, padding=0.0)

    def _draw_spectrogram(self):
        if not hasattr(self, "spectrogram_image") or not self.replay or not self.replay.frames: return
        time, freq, matrix = self.service.spectrogram(self.replay, self.channel_spin.value())
        low = self.spec_min.value()*1e6; high = self.spec_max.value()*1e6
        mask = (freq >= low) & (freq <= high)
        if not np.any(mask): return
        image = matrix[:, mask].T
        self.spectrogram_image.setImage(image, autoLevels=False, levels=(self.replay.display_db_min, self.replay.display_db_max))
        t_max = max(float(time[-1]) if len(time) else 0.0, self.replay.frame_interval_s)
        f_values = freq[mask]/1e6
        self.spectrogram_image.setRect(QRectF(0.0, float(f_values[0]), t_max, float(f_values[-1]-f_values[0] if len(f_values)>1 else .001)))
        self.spectrogram_plot.setTitle(f"CH{self.channel_spin.value()} · time-frequency relative level")

    def _selected_bands(self):
        return [(i, self.band_low[i].value()*1e6, self.band_high[i].value()*1e6) for i, enabled in enumerate(self.band_enabled) if enabled.isChecked() and self.band_high[i].value() > self.band_low[i].value()]

    def _draw_band_energy(self):
        if not hasattr(self, "band_plot"): return
        self.band_plot.clear()
        if not self.replay or not self.replay.frames: return
        time = np.arange(len(self.replay.frames))*self.replay.frame_interval_s
        for band_index, low, high in self._selected_bands():
            energy = self.service.band_energy(self.replay, low, high)
            for ch in range(8):
                y = energy[:, ch]
                valid = np.isfinite(y) & (y > 0)
                if not np.any(valid): continue
                ref = float(np.nanmax(y[valid])); db = np.full_like(y, -120.0)
                db[valid] = 10.0*np.log10(y[valid]/max(ref, np.finfo(float).tiny))
                pen = pg.mkPen(pg.intColor(ch, 8), width=2 if band_index == 0 else 1)
                self.band_plot.plot(time, db, pen=pen, name=f"B{band_index} CH{ch}")
        self.band_plot.setYRange(-60, 0, padding=.03)

    def _draw_statistics(self):
        if not hasattr(self, "stats_table") or not self.replay or not self.replay.frames: return
        bands = self._selected_bands()
        low, high = (bands[0][1], bands[0][2]) if bands else (0.25e6, 0.30e6)
        rows = self.service.frame_statistics(self.replay, self.frame_index, low, high)
        self.packet_label.setText(
            f"Measure #{self.frame_index+1} of {len(self.replay.frames)} · "
            f"Sonication frequency {self.replay.main_frequency_hz/1e6:.6f} MHz · "
            f"Band {low/1e6:.3f}–{high/1e6:.3f} MHz"
        )
        for r, data in enumerate(rows):
            values = [
                f"CH{int(data['channel'])}", self._fmt(data['raw_peak']), self._fmt(data['raw_rms']),
                self._fmt(data['dominant_hz']/1e6, 6), self._fmt(data['peak_db'], 2), self._fmt(data['band_energy'], 5),
            ]
            for c, value in enumerate(values): self.stats_table.setItem(r, c, QTableWidgetItem(value))

    @staticmethod
    def _fmt(value: float, digits: int = 3) -> str:
        return "N/A" if not np.isfinite(value) else f"{value:.{digits}g}"
