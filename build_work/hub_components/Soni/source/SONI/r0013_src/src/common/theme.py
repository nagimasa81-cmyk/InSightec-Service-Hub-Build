WS_STYLESHEET = r"""
QWidget { background: #dbeaf6; color: #17334a; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow, QMenuBar, QMenu, QToolBar, QStatusBar { background: #d5e6f4; color: #10283c; }
QMenu { border: 1px solid #577d9b; }
QPushButton, QToolButton { background: #edf5fb; color: #17334a; border: 1px solid #547b9a; border-radius: 2px; padding: 5px 10px; min-height: 22px; }
QPushButton:hover, QToolButton:hover { background: #f0f7fc; }
QPushButton:pressed, QToolButton:pressed { background: #7ca9ca; }
QPushButton#ReplayButton { background: #f7b325; color: #1b1b1b; border-radius: 12px; min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; padding: 0; }
QTreeWidget, QTableWidget, QListWidget { background: #f3f8fc; color: #10283c; border: 1px solid #557d9a; selection-background-color: #3f88bd; selection-color: white; }
QHeaderView::section { background: #cfe2f1; color: #10283c; border: 0; border-right: 1px solid #6d93af; border-bottom: 1px solid #6d93af; padding: 4px; }
QGroupBox { border: 1px solid #8aa9c1; border-radius: 1px; margin-top: 8px; padding-top: 8px; background: #e7f1f8; }
QGroupBox::title { subcontrol-origin: margin; left: 7px; padding: 0 4px; color: #16364f; font-weight: 600; }
QSplitter::handle { background: #9fb8cb; width: 2px; height: 2px; }
QSlider::groove:horizontal { height: 7px; background: #e4edf4; border: 1px solid #597f9d; }
QSlider::handle:horizontal { width: 13px; margin: -4px 0; background: #f5ad17; border: 1px solid #8a6414; border-radius: 6px; }
QComboBox, QSpinBox { background: #e6f0f7; color: #17334a; border: 1px solid #5f839e; padding: 3px; }
QLabel#SectionTitle { color: white; background: #1a1a1a; padding: 4px; font-weight: 600; }
QLabel#CurrentValue { color: #0a4f78; font-weight: 700; }
QFrame#BlackPanel { background: #050505; border: 1px solid #6a8ca4; }
"""

# Backward-compatible name used by application.py.
DARK_STYLESHEET = WS_STYLESHEET
