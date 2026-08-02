import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from src.common.constants import APP_NAME
from src.common.logger import configure_logging
from src.common.theme import DARK_STYLESHEET
from src.ui.main_window import MainWindow
from insightec_handoff import load_handoff

def run():
    handoff = load_handoff("sonication_analysis")
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    if handoff and handoff.auto_load:
        # Prefer the original dropped ZIP/folder. matched_files usually point to
        # individual files inside the Hub extraction workspace, which cannot be
        # opened as a complete Sonication study.
        source = handoff.preferred_dataset_source()
        handoff.mark(
            "sonication_analysis",
            "accepted",
            input_count=len(handoff.input_paths()),
            source=str(source or ""),
            source_kind=("directory" if source and source.is_dir() else "zip" if source and source.suffix.lower() == ".zip" else "file" if source else "missing"),
        )
        if source:
            QTimer.singleShot(0, lambda value=source: window.load(value))
    return app.exec()
