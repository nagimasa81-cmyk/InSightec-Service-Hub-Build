Log Merge Tool RC1 Commit0019 R1

Startup fixes:
- Added QTimer import required by Commit0018/0019 UI initialization.
- Added QRect import required by same-monitor window placement.
- Added QStandardItemModel and QStandardItem imports required by VIMeasure value view.

Distribution layout remains intentionally flat:
- EXE
- _internal
- BUILD_INFO/README/CHANGELOG
No extra application wrapper folder is required.
