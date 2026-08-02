from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class GuidePage:
    title: str
    body: str


@dataclass(frozen=True)
class GuideConfig:
    app_name: str
    settings_vendor: str = "InSightec"
    settings_product: str = "Application"
    guide_title: str | None = None
    startup_prompt_title: str | None = None
    exit_prompt_title: str | None = None


class GuideManager:
    """Reusable startup-guide and exit-confirmation manager for PySide6 apps."""

    DEFAULTS = {
        "ask_startup_guide": True,
        "show_guide_once": False,
    }

    def __init__(self, parent_window, config: GuideConfig, pages: Sequence[GuidePage]):
        self.parent_window = parent_window
        self.config = config
        self.pages = list(pages)
        self.settings = self._load_settings()
        self._allow_close = False

    @property
    def settings_path(self) -> Path:
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            folder = Path(base) / self.config.settings_vendor / self.config.settings_product
        else:
            folder = Path.home() / f".{self.config.settings_vendor.lower()}" / self.config.settings_product
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "settings.json"

    def _load_settings(self) -> dict:
        data = dict(self.DEFAULTS)
        try:
            loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for key in self.DEFAULTS:
                    if key in loaded:
                        data[key] = loaded[key]
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return data

    def _save_settings(self) -> None:
        try:
            self.settings_path.write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def schedule_startup_check(self) -> None:
        QTimer.singleShot(0, self.handle_startup_guide)

    def handle_startup_guide(self) -> None:
        if self.settings.get("show_guide_once", False):
            self.settings["show_guide_once"] = False
            self._save_settings()
            self.show_guide()
            return

        if not self.settings.get("ask_startup_guide", True):
            return

        box = QMessageBox(self.parent_window)
        box.setWindowTitle(
            self.config.startup_prompt_title or f"{self.config.app_name} Quick Guide"
        )
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("Would you like to view the Quick Guide and Guided Tour?")
        box.setInformativeText(
            "You can request the guide for the next startup from the exit confirmation window."
        )
        yes = box.addButton("Yes — Show Guide", QMessageBox.ButtonRole.AcceptRole)
        no = box.addButton("No — Do Not Ask Again", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(yes)
        box.exec()

        if box.clickedButton() is yes:
            self.show_guide()
        elif box.clickedButton() is no:
            self.settings["ask_startup_guide"] = False
            self._save_settings()

    def show_guide(self) -> None:
        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle(
            self.config.guide_title or f"{self.config.app_name} — Quick Guide and Guided Tour"
        )
        dialog.resize(820, 620)

        layout = QVBoxLayout(dialog)
        title = QLabel(f"{self.config.app_name} Quick Guide")
        title.setStyleSheet("font-size:18px;font-weight:600;color:#17365d;padding:4px")
        layout.addWidget(title)

        stack = QStackedWidget()
        layout.addWidget(stack, 1)

        for page_data in self.pages:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            heading = QLabel(page_data.title)
            heading.setStyleSheet("font-size:16px;font-weight:600;color:#2d5d88")
            body = QTextBrowser()
            body.setHtml(
                f"<div style='font-size:14px;line-height:1.55'>{page_data.body}</div>"
            )
            page_layout.addWidget(heading)
            page_layout.addWidget(body, 1)
            stack.addWidget(page)

        nav = QHBoxLayout()
        back = QPushButton("Back")
        next_button = QPushButton("Next")
        close_button = QPushButton("Close Guide")
        nav.addWidget(back)
        nav.addStretch()
        nav.addWidget(next_button)
        nav.addWidget(close_button)
        layout.addLayout(nav)

        def update_navigation() -> None:
            back.setEnabled(stack.currentIndex() > 0)
            next_button.setVisible(stack.currentIndex() < stack.count() - 1)
            close_button.setVisible(stack.currentIndex() == stack.count() - 1)

        back.clicked.connect(
            lambda: (stack.setCurrentIndex(max(0, stack.currentIndex() - 1)), update_navigation())
        )
        next_button.clicked.connect(
            lambda: (
                stack.setCurrentIndex(min(stack.count() - 1, stack.currentIndex() + 1)),
                update_navigation(),
            )
        )
        close_button.clicked.connect(dialog.accept)
        update_navigation()
        dialog.exec()

    def handle_close_event(self, event, cleanup_callback=None) -> None:
        if self._allow_close:
            event.accept()
            return

        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle(
            self.config.exit_prompt_title or f"Exit {self.config.app_name}"
        )
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        label = QLabel(f"Exit {self.config.app_name}?")
        label.setStyleSheet("font-size:15px;font-weight:600")
        layout.addWidget(label)

        check = QCheckBox("Show the guide and guided tour at the next startup")
        check.setChecked(False)
        layout.addWidget(check)

        buttons = QDialogButtonBox()
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        exit_button = buttons.addButton("Exit", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button.clicked.connect(dialog.reject)
        exit_button.clicked.connect(dialog.accept)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if check.isChecked():
                self.settings["show_guide_once"] = True
                self._save_settings()
            self._allow_close = True
            if cleanup_callback is not None:
                cleanup_callback()
            event.accept()
        else:
            event.ignore()

    def reset_startup_prompt(self) -> None:
        """Optional helper for a Help/Settings menu action."""
        self.settings["ask_startup_guide"] = True
        self.settings["show_guide_once"] = False
        self._save_settings()
