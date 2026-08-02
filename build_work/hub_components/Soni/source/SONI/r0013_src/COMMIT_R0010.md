# RC2-R0010 Runtime Startup Regression Recovery

- Removed the stale `_render_replay_selection` registration that crashed `MainWindow.__init__` in packaged EXEs.
- Restored the RC1 direct-render path as the only authoritative main-view runtime path.
- Added missing `_replay_duration_s()` and `_seconds_to_index()` helpers used by info and chart interaction paths.
- Added static MainWindow method-reference regression tests so missing callbacks fail before packaging.
- Added a startup-construction source audit covering every `self.<private_method>` reference.
