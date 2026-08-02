# R0010 Triple Check Report

## 1. Startup-path audit

The packaged EXE crash was caused by `MainWindow.__init__` registering a callback that no longer existed:

```python
self.replay_views.register("atomic_frame_snapshot", self._render_replay_selection)
```

The stale registration has been removed. RC1 direct rendering through `set_frame()` remains authoritative.

Two additional runtime method omissions were found and repaired:

- `_replay_duration_s()`
- `_seconds_to_index()`

These methods are used by the info window and chart click/hover paths and would otherwise fail after startup.

## 2. Static and regression checks

- Parsed `MainWindow` with Python AST.
- Verified every private `self._...` reference resolves to a method or initialized attribute.
- Verified no stale `_render_replay_selection` registration remains.
- Verified chart time mapping helpers exist.
- Compiled every Python source file.

## 3. Test and package checks

- `pytest`: 41 passed.
- `verify_source.py`: `VERIFY_SOURCE_OK`.
- `compileall`: passed.
- ZIP integrity: checked after packaging.

## Runtime limitation

The current Linux verification environment does not include PySide6, so a real Windows GUI/EXE launch cannot be performed here. The exact reported constructor crash and all additional statically detectable missing MainWindow callbacks were repaired before packaging.
