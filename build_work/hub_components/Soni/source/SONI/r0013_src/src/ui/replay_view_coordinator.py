from __future__ import annotations

from collections import OrderedDict
from typing import Callable

from src.core.replay_context import ReplayContext, ReplaySelection


class ReplayViewCoordinator:
    """One render pipeline for every frame-synchronized replay view.

    Controls mutate ReplayContext only. The coordinator fans the immutable
    selection out to registered views in a fixed order. This prevents image,
    temperature, spectrum and acoustic panels from maintaining independent
    frame cursors.
    """

    def __init__(self, context: ReplayContext) -> None:
        self.context = context
        self._views: OrderedDict[str, Callable[[ReplaySelection], None]] = OrderedDict()
        self._rendering = False
        self._pending_selection: ReplaySelection | None = None
        self.render_count = 0
        context.selectionChanged.connect(self.render)
        context.refreshRequested.connect(self.render)

    def register(self, name: str, callback: Callable[[ReplaySelection], None]) -> None:
        if not name or name in self._views:
            raise ValueError(f"Duplicate or empty replay view name: {name!r}")
        self._views[name] = callback

    @property
    def view_names(self) -> tuple[str, ...]:
        return tuple(self._views)

    def render(self, selection: ReplaySelection) -> None:
        # Do not lose state changes that occur while a view is rendering. Keep
        # only the latest complete selection and render it immediately after the
        # current pass. This prevents stale image/spectrum combinations.
        if self._rendering:
            self._pending_selection = selection
            return
        current = selection
        while current is not None:
            self._rendering = True
            self._pending_selection = None
            try:
                for callback in tuple(self._views.values()):
                    callback(current)
                self.render_count += 1
            finally:
                self._rendering = False
            current = self._pending_selection
