
"""Integrated Sonication replay and synchronized multi-source analysis."""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget, QHeaderView,
)


def _value(record: Any, key: str, default=None):
    if hasattr(record, "get"):
        return record.get(key, default)
    return getattr(record, key, default)


def _timestamp(record: Any) -> datetime | None:
    value = _value(record, "_ts") or _value(record, "Timestamp") or _value(record, "timestamp")
    return value if isinstance(value, datetime) else None


def _message(record: Any) -> str:
    return str(_value(record, "Message", "") or _value(record, "message", ""))


def _numeric(message: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                pass
    return None


class SonicationReplayConsole(QWidget):
    """Synchronizes Acquisition, Spectrum, VIMeasure and temperature streams."""

    timeChanged = Signal(object)

    def __init__(self, investigation):
        super().__init__(investigation)
        self.investigation = investigation
        self.events: list[dict[str, Any]] = []
        self.timeline_start: datetime | None = None
        self.timeline_end: datetime | None = None
        self.current_time: datetime | None = None
        self._playing = False

        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)

        top = QHBoxLayout()
        title = QLabel("Sonication Replay & Synchronized Analysis")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#005DAA;")
        self.sonication_combo = QComboBox()
        self.sonication_combo.currentIndexChanged.connect(self._sonication_changed)
        self.window_combo = QComboBox()
        for label, seconds in [
            ("±2 sec", 2), ("±5 sec", 5), ("±10 sec", 10),
            ("±30 sec", 30), ("Full selected sonication", -1),
        ]:
            self.window_combo.addItem(label, seconds)
        self.refresh_button = QPushButton("Build Synchronized Timeline")
        self.refresh_button.clicked.connect(self.refresh)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QLabel("Sonication:"))
        top.addWidget(self.sonication_combo)
        top.addWidget(QLabel("Window:"))
        top.addWidget(self.window_combo)
        top.addWidget(self.refresh_button)
        root.addLayout(top)

        self.status = QLabel("Run Sonication Investigation, then build the synchronized timeline.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            "background:#EAF2F8;border:1px solid #CBD5E1;"
            "border-radius:4px;padding:8px;"
        )
        root.addWidget(self.status)

        replay = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_play)
        self.step_back = QPushButton("◀")
        self.step_forward = QPushButton("▶")
        self.step_back.clicked.connect(lambda: self._step(-1))
        self.step_forward.clicked.connect(lambda: self._step(1))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.valueChanged.connect(self._slider_changed)
        self.time_label = QLabel("--:--:--.---")
        replay.addWidget(self.play_button)
        replay.addWidget(self.step_back)
        replay.addWidget(self.step_forward)
        replay.addWidget(self.slider, 1)
        replay.addWidget(self.time_label)
        root.addLayout(replay)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)

        cards = QHBoxLayout()
        self.card_labels: dict[str, QLabel] = {}
        for key, label in [
            ("power", "Acoustic Power"),
            ("temperature", "Temperature"),
            ("reflection", "Reflection"),
            ("spectrum", "Spectrum"),
            ("stable", "Stable Cavitation"),
            ("inertial", "Inertial Cavitation"),
            ("broadband", "Broadband"),
        ]:
            box = QGroupBox(label)
            layout = QVBoxLayout(box)
            value = QLabel("—")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("font-size:18px;font-weight:700;")
            layout.addWidget(value)
            cards.addWidget(box)
            self.card_labels[key] = value
        root.addLayout(cards)

        splitter = QSplitter(Qt.Vertical)
        root.addWidget(splitter, 1)

        self.sync_table = QTableWidget(0, 6)
        self.sync_table.setHorizontalHeaderLabels(
            ["Offset", "Timestamp", "Source", "Metric", "Value", "Message"]
        )
        self.sync_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.sync_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        splitter.addWidget(self.sync_table)

        lower_tabs = QTabWidget()
        self.correlation_table = QTableWidget(0, 4)
        self.correlation_table.setHorizontalHeaderLabels(
            ["Relationship", "Samples", "Correlation", "Interpretation"]
        )
        self.correlation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lower_tabs.addTab(self.correlation_table, "Cross-source Correlation")

        self.hydro_table = QTableWidget(0, 7)
        self.hydro_table.setHorizontalHeaderLabels(
            ["Hydrophone", "Peak Freq.", "Peak Amp.", "Subharmonic",
             "Ultraharmonic", "Broadband", "Candidate"]
        )
        self.hydro_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lower_tabs.addTab(self.hydro_table, "Hydrophone / Cavitation")
        splitter.addWidget(lower_tabs)
        splitter.setSizes([520, 250])

    def refresh(self) -> None:
        source_records = self.investigation.source_records
        self.events = []

        for source, records in source_records.items():
            for record in records:
                ts = _timestamp(record)
                if ts is None:
                    continue
                msg = _message(record)
                metric, value = self._classify_metric(source, msg)
                self.events.append({
                    "timestamp": ts,
                    "source": source,
                    "metric": metric,
                    "value": value,
                    "message": msg,
                })

        spectrum_widget = getattr(self.investigation, "spectrum_analysis", None)
        if spectrum_widget is not None:
            for dump in getattr(spectrum_widget, "dumps", []):
                if dump.timestamp is None:
                    continue
                self.events.append({
                    "timestamp": dump.timestamp,
                    "source": "Spectrum",
                    "metric": "Spectrum Dump",
                    "value": dump.acoustic_power,
                    "message": dump.path.name,
                    "dump": dump,
                })

        self.events.sort(key=lambda item: item["timestamp"])
        sonications = self._build_sonications()

        self.sonication_combo.blockSignals(True)
        self.sonication_combo.clear()
        for index, item in enumerate(sonications, 1):
            label = f"Sonication {index} — {item['start'].strftime('%H:%M:%S.%f')[:-3]}"
            self.sonication_combo.addItem(label, item)
        self.sonication_combo.blockSignals(False)

        if sonications:
            self.sonication_combo.setCurrentIndex(0)
            self._sonication_changed(0)
        else:
            self.status.setText(
                f"Indexed {len(self.events):,} timestamped events, but no "
                "Sonication start marker was detected."
            )
            self._populate_tables(self.events)

    def _classify_metric(self, source: str, message: str) -> tuple[str, float | str]:
        power = _numeric(message, [
            r"(?:m_PowerS|SonicAcousticPower)<([+-]?\d+(?:\.\d+)?)>",
            r"Acoustic\s*Power[^0-9+-]*([+-]?\d+(?:\.\d+)?)",
        ])
        if power is not None:
            return "Acoustic Power", power

        temperature = _numeric(message, [
            r"(?:temperature|temp)[^0-9+-]*([+-]?\d+(?:\.\d+)?)",
            r"(?:MaxTemp|PeakTemp)[^0-9+-]*([+-]?\d+(?:\.\d+)?)",
        ])
        if temperature is not None:
            return "Temperature", temperature

        reflection = _numeric(message, [
            r"Max Value=\s*\(([+-]?\d+(?:\.\d+)?)\)",
            r"reflection[^0-9+-]*([+-]?\d+(?:\.\d+)?)",
        ])
        if reflection is not None:
            return "Reflection", reflection

        if "saving fft data" in message.lower() or "spectrum_" in message.lower():
            return "Spectrum Save", 1.0
        if "sonication" in message.lower():
            return "Sonication", message
        if "dangerous channel" in message.lower() or "high reflection channel" in message.lower():
            count = _numeric(message, [r"(?:Detected\s*<|channels?[^0-9]*)(\d+)"])
            return "Dangerous Channel", count if count is not None else 1.0
        return "Event", ""

    def _build_sonications(self) -> list[dict[str, datetime]]:
        starts = [
            item["timestamp"] for item in self.events
            if item["metric"] == "Sonication"
            and any(token in item["message"].lower() for token in ("start", "begin", "sonication"))
        ]
        unique: list[datetime] = []
        for ts in starts:
            if not unique or abs((ts - unique[-1]).total_seconds()) > 1.0:
                unique.append(ts)
        output = []
        for index, start in enumerate(unique):
            end = unique[index + 1] if index + 1 < len(unique) else start + timedelta(seconds=30)
            output.append({"start": start, "end": end})
        return output

    def _sonication_changed(self, index: int) -> None:
        item = self.sonication_combo.itemData(index)
        if not isinstance(item, dict):
            return
        self.timeline_start = item["start"]
        self.timeline_end = item["end"]
        self.slider.setValue(0)
        self.current_time = self.timeline_start
        selected = [
            event for event in self.events
            if self.timeline_start - timedelta(seconds=5)
            <= event["timestamp"]
            <= self.timeline_end + timedelta(seconds=5)
        ]
        self._populate_tables(selected)
        self._update_current()
        self.status.setText(
            f"Selected {self.sonication_combo.currentText()}. "
            f"Synchronized events: {len(selected):,}. "
            "Replay updates Acquisition, Spectrum, VIMeasure and temperature cards."
        )

    def _populate_tables(self, events: list[dict[str, Any]]) -> None:
        start = self.timeline_start or (events[0]["timestamp"] if events else None)
        self.sync_table.setRowCount(len(events))
        for row, event in enumerate(events):
            offset = (
                (event["timestamp"] - start).total_seconds()
                if start is not None else 0.0
            )
            values = [
                f"{offset:+.3f}s",
                event["timestamp"].strftime("%Y/%m/%d %H:%M:%S.%f")[:-3],
                event["source"],
                event["metric"],
                event["value"],
                event["message"],
            ]
            for column, value in enumerate(values):
                self.sync_table.setItem(row, column, QTableWidgetItem(str(value)))

        self._populate_correlations(events)
        self._populate_hydrophones(events)

    def _populate_correlations(self, events: list[dict[str, Any]]) -> None:
        metrics: dict[str, list[tuple[datetime, float]]] = {}
        for event in events:
            if isinstance(event["value"], (int, float)):
                metrics.setdefault(event["metric"], []).append(
                    (event["timestamp"], float(event["value"]))
                )

        pairs = [
            ("Acoustic Power", "Temperature"),
            ("Acoustic Power", "Reflection"),
            ("Reflection", "Dangerous Channel"),
            ("Acoustic Power", "Spectrum Save"),
        ]
        rows = []
        for left, right in pairs:
            correlation, samples = self._nearest_correlation(
                metrics.get(left, []), metrics.get(right, [])
            )
            interpretation = (
                "Strong" if abs(correlation) >= 0.7 else
                "Moderate" if abs(correlation) >= 0.4 else
                "Weak / insufficient"
            )
            rows.append((f"{left} ↔ {right}", samples, correlation, interpretation))

        self.correlation_table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                text = f"{value:.3f}" if isinstance(value, float) else str(value)
                self.correlation_table.setItem(r, c, QTableWidgetItem(text))

    def _nearest_correlation(
        self,
        left: list[tuple[datetime, float]],
        right: list[tuple[datetime, float]],
    ) -> tuple[float, int]:
        pairs = []
        for ts, value in left:
            candidates = [
                (abs((other_ts - ts).total_seconds()), other_value)
                for other_ts, other_value in right
            ]
            if not candidates:
                continue
            distance, other_value = min(candidates, key=lambda item: item[0])
            if distance <= 1.0:
                pairs.append((value, other_value))
        if len(pairs) < 3:
            return 0.0, len(pairs)
        xs = [item[0] for item in pairs]
        ys = [item[1] for item in pairs]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
        denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
        denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
        if denom_x == 0 or denom_y == 0:
            return 0.0, len(pairs)
        return numerator / (denom_x * denom_y), len(pairs)

    def _populate_hydrophones(self, events: list[dict[str, Any]]) -> None:
        dumps = [event.get("dump") for event in events if event.get("dump") is not None]
        rows = []
        for dump in dumps[:1]:
            fundamental = max(1.0, dump.main_frequency_hz)
            for index, block in enumerate(dump.blocks):
                if not block:
                    continue
                peak_frequency, peak_amplitude = dump.peak(index)
                sub = self._band_energy(block, dump.nyquist_hz, fundamental * 0.5)
                ultra = self._band_energy(block, dump.nyquist_hz, fundamental * 1.5)
                broadband = self._broadband_score(block)
                stable = max(sub, ultra)
                inertial = broadband
                candidate = (
                    "Stable + Inertial" if stable > 2.5 and inertial > 2.5 else
                    "Stable candidate" if stable > 2.5 else
                    "Inertial candidate" if inertial > 2.5 else
                    "Low"
                )
                rows.append((
                    f"H{index}",
                    f"{peak_frequency/1_000_000:.6f} MHz",
                    f"{peak_amplitude:.6g}",
                    f"{sub:.2f}",
                    f"{ultra:.2f}",
                    f"{broadband:.2f}",
                    candidate,
                ))

        self.hydro_table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                self.hydro_table.setItem(r, c, QTableWidgetItem(str(value)))

    def _band_energy(self, values: list[float], nyquist: float, target: float) -> float:
        if not values or target <= 0 or target >= nyquist:
            return 0.0
        center = int(target / nyquist * max(1, len(values) - 1))
        window = values[max(0, center - 2): min(len(values), center + 3)]
        baseline = sum(values) / max(1, len(values))
        return (max(window, default=0.0) / max(1e-12, baseline))

    def _broadband_score(self, values: list[float]) -> float:
        if len(values) < 8:
            return 0.0
        sorted_values = sorted(values)
        median = sorted_values[len(sorted_values) // 2]
        upper = sorted_values[int(len(sorted_values) * 0.75):]
        return (sum(upper) / max(1, len(upper))) / max(1e-12, median)

    def _slider_changed(self, value: int) -> None:
        if self.timeline_start is None or self.timeline_end is None:
            return
        duration = max(0.001, (self.timeline_end - self.timeline_start).total_seconds())
        self.current_time = self.timeline_start + timedelta(seconds=duration * value / 1000.0)
        self._update_current()

    def _update_current(self) -> None:
        if self.current_time is None:
            return
        self.time_label.setText(self.current_time.strftime("%H:%M:%S.%f")[:-3])
        window = self.window_combo.currentData()
        seconds = 5 if not isinstance(window, int) or window < 0 else window
        nearby = [
            event for event in self.events
            if abs((event["timestamp"] - self.current_time).total_seconds()) <= seconds
        ]

        latest: dict[str, Any] = {}
        for event in nearby:
            latest[event["metric"]] = event["value"]

        self.card_labels["power"].setText(self._format(latest.get("Acoustic Power"), " W"))
        self.card_labels["temperature"].setText(self._format(latest.get("Temperature"), " °C"))
        self.card_labels["reflection"].setText(self._format(latest.get("Reflection"), ""))
        self.card_labels["spectrum"].setText(
            "Detected" if "Spectrum Save" in latest else "—"
        )

        stable = inertial = broadband = None
        for row in range(self.hydro_table.rowCount()):
            try:
                stable_value = float(self.hydro_table.item(row, 3).text())
                ultra_value = float(self.hydro_table.item(row, 4).text())
                broad_value = float(self.hydro_table.item(row, 5).text())
                stable = max(stable or 0.0, stable_value, ultra_value)
                inertial = max(inertial or 0.0, broad_value)
                broadband = max(broadband or 0.0, broad_value)
            except Exception:
                pass
        self.card_labels["stable"].setText(self._format(stable, ""))
        self.card_labels["inertial"].setText(self._format(inertial, ""))
        self.card_labels["broadband"].setText(self._format(broadband, ""))

        self.timeChanged.emit(self.current_time)

    def _format(self, value, suffix: str) -> str:
        if isinstance(value, (int, float)):
            return f"{value:.3f}{suffix}"
        return "—"

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        if self._playing:
            if self.slider.value() >= self.slider.maximum():
                self.slider.setValue(0)
            self.timer.start()
            self.play_button.setText("Pause")
        else:
            self.timer.stop()
            self.play_button.setText("Play")

    def _tick(self) -> None:
        value = self.slider.value() + 5
        if value >= self.slider.maximum():
            value = self.slider.maximum()
            self._playing = False
            self.timer.stop()
            self.play_button.setText("Play")
        self.slider.setValue(value)

    def _step(self, direction: int) -> None:
        self.slider.setValue(
            max(self.slider.minimum(), min(self.slider.maximum(), self.slider.value() + direction * 10))
        )
