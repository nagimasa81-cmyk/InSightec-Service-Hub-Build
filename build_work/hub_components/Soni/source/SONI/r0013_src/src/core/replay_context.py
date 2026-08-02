from __future__ import annotations

from dataclasses import dataclass, replace

try:
    from PySide6.QtCore import QObject, Signal
except ModuleNotFoundError:  # allows headless source verification without Qt
    class _BoundSignal:
        def __init__(self):
            self._slots = []
        def connect(self, slot):
            self._slots.append(slot)
        def emit(self, *args):
            for slot in list(self._slots):
                slot(*args)

    class Signal:
        def __init__(self, *_types):
            self._name = None
        def __set_name__(self, owner, name):
            self._name = f"__signal_{name}"
        def __get__(self, instance, owner):
            if instance is None:
                return self
            signal = instance.__dict__.get(self._name)
            if signal is None:
                signal = _BoundSignal()
                instance.__dict__[self._name] = signal
            return signal

    class QObject:
        def __init__(self, parent=None):
            self._parent = parent


@dataclass(frozen=True, slots=True)
class ReplaySelection:
    """Single source of truth for all replay navigation state."""

    sonication_index: int = -1
    sonication_count: int = 0
    frame_index: int = 0
    frame_count: int = 0
    channel_index: int = 0

    def normalized(self) -> "ReplaySelection":
        son_count = max(0, int(self.sonication_count))
        frame_count = max(0, int(self.frame_count))
        son = -1 if son_count == 0 else min(max(0, int(self.sonication_index)), son_count - 1)
        frame = 0 if frame_count == 0 else min(max(0, int(self.frame_index)), frame_count - 1)
        channel = min(max(0, int(self.channel_index)), 7)
        return replace(
            self,
            sonication_index=son,
            sonication_count=son_count,
            frame_index=frame,
            frame_count=frame_count,
            channel_index=channel,
        )


class ReplayContext(QObject):
    """Central replay state used by every synchronized view.

    UI controls must request a state change here. Views must not keep an
    independent frame/sonication cursor.  Signals include the complete state so
    late subscribers can redraw deterministically.
    """

    selectionChanged = Signal(object)
    sonicationChanged = Signal(object)
    frameChanged = Signal(object)
    channelChanged = Signal(object)
    refreshRequested = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._selection = ReplaySelection()

    @property
    def selection(self) -> ReplaySelection:
        return self._selection

    def configure_study(self, sonication_count: int) -> ReplaySelection:
        return self._commit(replace(self._selection, sonication_count=sonication_count))

    def select_sonication(self, index: int, frame_count: int, initial_frame: int = 0) -> ReplaySelection:
        return self._commit(
            replace(
                self._selection,
                sonication_index=index,
                frame_count=frame_count,
                frame_index=initial_frame,
            )
        )

    def select_frame(self, index: int) -> ReplaySelection:
        return self._commit(replace(self._selection, frame_index=index))

    def step_frame(self, delta: int, *, wrap: bool = False) -> ReplaySelection:
        current = self._selection
        if current.frame_count <= 0:
            return current
        target = current.frame_index + int(delta)
        if wrap:
            target %= current.frame_count
        return self.select_frame(target)

    def select_channel(self, index: int) -> ReplaySelection:
        return self._commit(replace(self._selection, channel_index=index))

    def refresh(self) -> ReplaySelection:
        """Request deterministic redraw without mutating navigation state."""
        self.refreshRequested.emit(self._selection)
        return self._selection

    def _commit(self, candidate: ReplaySelection) -> ReplaySelection:
        previous = self._selection
        current = candidate.normalized()
        if current == previous:
            return current
        self._selection = current
        self.selectionChanged.emit(current)
        if (current.sonication_index, current.sonication_count) != (
            previous.sonication_index,
            previous.sonication_count,
        ):
            self.sonicationChanged.emit(current)
        if (current.frame_index, current.frame_count) != (previous.frame_index, previous.frame_count):
            self.frameChanged.emit(current)
        if current.channel_index != previous.channel_index:
            self.channelChanged.emit(current)
        return current
