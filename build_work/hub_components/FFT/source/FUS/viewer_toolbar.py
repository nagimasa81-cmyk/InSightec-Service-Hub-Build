from __future__ import annotations

"""Reusable top toolbar for image display and navigation."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class ViewerToolbar(QWidget):
    displayModeRequested = Signal(str)
    previousRequested = Signal()
    nextRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewerTopDisplayNavigationToolbar")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Display"))
        self.fft_button = self._mode_button("FFT")
        self.original_button = self._mode_button("Original")
        self.both_button = self._mode_button("Both")
        for button in (self.fft_button, self.original_button, self.both_button):
            layout.addWidget(button)

        layout.addStretch(1)
        self.previous_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.slice_label = QLabel("Slice: -")
        self.previous_button.clicked.connect(self.previousRequested)
        self.next_button.clicked.connect(self.nextRequested)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.slice_label)
        layout.addStretch(1)

    def _mode_button(self, mode: str) -> QPushButton:
        button = QPushButton(mode)
        button.setCheckable(True)
        button.clicked.connect(
            lambda _checked=False, selected=mode: self.displayModeRequested.emit(selected)
        )
        return button

    def set_display_mode(self, mode: str) -> None:
        for name, button in (
            ("FFT", self.fft_button),
            ("Original", self.original_button),
            ("Both", self.both_button),
        ):
            button.blockSignals(True)
            button.setChecked(name == mode)
            button.blockSignals(False)
    def set_navigation_state(
        self,
        *,
        label: str,
        has_previous: bool,
        has_next: bool,
    ) -> None:
        """Update label and boundary-aware button availability atomically."""
        self.slice_label.setText(str(label))
        self.previous_button.setEnabled(bool(has_previous))
        self.next_button.setEnabled(bool(has_next))

    def current_display_mode(self) -> str:
        for name, button in (
            ("FFT", self.fft_button),
            ("Original", self.original_button),
            ("Both", self.both_button),
        ):
            if button.isChecked():
                return name
        return "Both"

