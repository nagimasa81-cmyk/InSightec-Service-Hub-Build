from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QMessageBox,
)

DEFAULT_SETTINGS = {
    "schema_version": "1.0",
    "show_startup_prompt": True,
    "show_guide_next_startup": False,
    "do_not_ask_again": False,
    "guide_version": "1.0",
    "last_completed_guide_version": "",
}

DEFAULT_STEPS = [
    {"id": "welcome", "title": "Welcome", "body": "Welcome to Complaint Service Hub. This guide introduces the main complaint workflow."},
    {"id": "language", "title": "Language selection", "body": "Choose the display language from the language selector in the upper-right area.", "target": "lang_cb"},
    {"id": "complaint", "title": "Create Complaint", "body": "Open Complaint from the navigation panel or launch pad to start a new complaint.", "target": "nav_complaint"},
    {"id": "basic", "title": "Basic information", "body": "Complete all required fields in the Basic tab. Missing required fields are highlighted in red."},
    {"id": "medical", "title": "Medical information", "body": "Review and complete the required Medical tab fields before creating feedback."},
    {"id": "additional", "title": "Additional information", "body": "Complete the Additional tab and verify that no required field remains red."},
    {"id": "feedback", "title": "Create Feedback", "body": "Create Feedback prepares the English email. Outlook is used when available; otherwise use the copyable template."},
    {"id": "finish", "title": "Ready", "body": "The basic guide is complete. You can restart it later from the Guide menu."},
]

TRANSLATIONS = {
    "en": {
        "welcome_title": "Welcome to Complaint Service Hub", "welcome_body": "Would you like to view the quick guide and guided tour?",
        "start_guide": "Start Guide", "not_now": "Not Now", "dont_ask": "Don't ask again", "previous": "Previous", "next": "Next",
        "skip": "Skip", "finish": "Finish", "guide": "Guide", "go_to_section": "Go to this section",
        "never_show": "Do not show this guide again", "progress": "Step {current} / {total}", "image_area": "Guide image area",
        "complete_title": "Guide complete", "complete_body": "Create a complaint now?", "yes": "Yes", "no": "No",
        "guide_error_title": "Guide error", "guide_error_body": "The guide action could not be completed.",
        "exit_title": "Exit Complaint Service Hub?", "exit_body": "Are you sure you want to close the application?",
        "show_next": "Show the guide and guided tour at the next startup", "cancel": "Cancel", "exit": "Exit",
    },
    "ja": {
        "welcome_title": "Complaint Service Hubへようこそ", "welcome_body": "クイックガイドとガイドツアーを表示しますか？",
        "start_guide": "ガイドを開始", "not_now": "今回は表示しない", "dont_ask": "次回から確認しない", "previous": "戻る", "next": "次へ",
        "skip": "スキップ", "finish": "完了", "guide": "ガイド", "go_to_section": "該当画面へ移動",
        "never_show": "このガイドを今後表示しない", "progress": "ステップ {current} / {total}", "image_area": "ガイド画像エリア",
        "complete_title": "ガイド完了", "complete_body": "続けてComplaintを作成しますか？", "yes": "はい", "no": "いいえ",
        "guide_error_title": "ガイドエラー", "guide_error_body": "ガイド操作を完了できませんでした。",
        "exit_title": "Complaint Service Hubを終了しますか？", "exit_body": "アプリケーションを閉じてもよろしいですか？",
        "show_next": "次回起動時にガイドとツアーを表示する", "cancel": "キャンセル", "exit": "終了",
    },
    "ko": {
        "welcome_title": "Complaint Service Hub에 오신 것을 환영합니다", "welcome_body": "빠른 가이드와 안내 투어를 표시하시겠습니까?",
        "start_guide": "가이드 시작", "not_now": "나중에", "dont_ask": "다시 묻지 않기", "previous": "이전", "next": "다음",
        "skip": "건너뛰기", "finish": "완료", "guide": "가이드", "go_to_section": "해당 화면으로 이동",
        "never_show": "이 가이드를 다시 표시하지 않기", "progress": "단계 {current} / {total}", "image_area": "가이드 이미지 영역",
        "complete_title": "가이드 완료", "complete_body": "지금 Complaint를 작성하시겠습니까?", "yes": "예", "no": "아니요",
        "guide_error_title": "가이드 오류", "guide_error_body": "가이드 작업을 완료할 수 없습니다.",
        "exit_title": "Complaint Service Hub를 종료하시겠습니까?", "exit_body": "애플리케이션을 닫으시겠습니까?",
        "show_next": "다음 시작 시 가이드와 투어 표시", "cancel": "취소", "exit": "종료",
    },
    "th": {
        "welcome_title": "ยินดีต้อนรับสู่ Complaint Service Hub", "welcome_body": "ต้องการดูคู่มือฉบับย่อและทัวร์แนะนำหรือไม่?",
        "start_guide": "เริ่มคู่มือ", "not_now": "ไม่ใช่ตอนนี้", "dont_ask": "ไม่ต้องถามอีก", "previous": "ก่อนหน้า", "next": "ถัดไป",
        "skip": "ข้าม", "finish": "เสร็จสิ้น", "guide": "คู่มือ", "go_to_section": "ไปยังหน้าที่เกี่ยวข้อง",
        "never_show": "ไม่ต้องแสดงคู่มือนี้อีก", "progress": "ขั้นตอน {current} / {total}", "image_area": "พื้นที่รูปภาพคู่มือ",
        "complete_title": "คู่มือเสร็จสมบูรณ์", "complete_body": "สร้าง Complaint ตอนนี้หรือไม่?", "yes": "ใช่", "no": "ไม่",
        "guide_error_title": "ข้อผิดพลาดของคู่มือ", "guide_error_body": "ไม่สามารถดำเนินการคู่มือให้เสร็จสิ้นได้",
        "exit_title": "ออกจาก Complaint Service Hub?", "exit_body": "ต้องการปิดแอปพลิเคชันหรือไม่?",
        "show_next": "แสดงคู่มือและทัวร์เมื่อเริ่มครั้งถัดไป", "cancel": "ยกเลิก", "exit": "ออก",
    },
    "zh-TW": {
        "welcome_title": "歡迎使用 Complaint Service Hub", "welcome_body": "是否要顯示快速指南與導覽?",
        "start_guide": "開始指南", "not_now": "稍後", "dont_ask": "不再詢問", "previous": "上一步", "next": "下一步",
        "skip": "略過", "finish": "完成", "guide": "指南", "go_to_section": "前往相關頁面",
        "never_show": "不要再顯示此指南", "progress": "步驟 {current} / {total}", "image_area": "指南圖片區域",
        "complete_title": "指南完成", "complete_body": "現在建立 Complaint 嗎?", "yes": "是", "no": "否",
        "guide_error_title": "指南錯誤", "guide_error_body": "無法完成指南操作。",
        "exit_title": "結束 Complaint Service Hub?", "exit_body": "確定要關閉應用程式嗎?",
        "show_next": "下次啟動時顯示指南與導覽", "cancel": "取消", "exit": "結束",
    },
    "zh-CN": {
        "welcome_title": "欢迎使用 Complaint Service Hub", "welcome_body": "是否显示快速指南和引导教程？",
        "start_guide": "开始指南", "not_now": "稍后", "dont_ask": "不再询问", "previous": "上一步", "next": "下一步",
        "skip": "跳过", "finish": "完成", "guide": "指南", "go_to_section": "前往相关页面",
        "never_show": "不再显示此指南", "progress": "步骤 {current} / {total}", "image_area": "指南图片区域",
        "complete_title": "指南完成", "complete_body": "现在创建 Complaint 吗？", "yes": "是", "no": "否",
        "guide_error_title": "指南错误", "guide_error_body": "无法完成指南操作。",
        "exit_title": "退出 Complaint Service Hub？", "exit_body": "确定要关闭应用程序吗？",
        "show_next": "下次启动时显示指南和教程", "cancel": "取消", "exit": "退出",
    },
    "hi": {
        "welcome_title": "Complaint Service Hub में आपका स्वागत है", "welcome_body": "क्या आप त्वरित गाइड और निर्देशित टूर देखना चाहते हैं?",
        "start_guide": "गाइड शुरू करें", "not_now": "अभी नहीं", "dont_ask": "फिर न पूछें", "previous": "पिछला", "next": "अगला",
        "skip": "छोड़ें", "finish": "पूर्ण", "guide": "गाइड", "go_to_section": "संबंधित स्क्रीन पर जाएँ",
        "never_show": "यह गाइड फिर न दिखाएँ", "progress": "चरण {current} / {total}", "image_area": "गाइड चित्र क्षेत्र",
        "complete_title": "गाइड पूर्ण", "complete_body": "क्या अभी Complaint बनाना है?", "yes": "हाँ", "no": "नहीं",
        "guide_error_title": "गाइड त्रुटि", "guide_error_body": "गाइड कार्रवाई पूरी नहीं की जा सकी।",
        "exit_title": "Complaint Service Hub बंद करें?", "exit_body": "क्या आप एप्लिकेशन बंद करना चाहते हैं?",
        "show_next": "अगली बार शुरू होने पर गाइड और टूर दिखाएँ", "cancel": "रद्द करें", "exit": "बंद करें",
    },
}


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class WelcomeDialog(QDialog):
    def __init__(self, text: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(text["welcome_title"])
        self.setModal(True)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        title = QLabel(text["welcome_title"])
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setWordWrap(True)
        body = QLabel(text["welcome_body"])
        body.setWordWrap(True)
        body.setStyleSheet("color:#334155; padding:8px 0 16px 0;")
        self.do_not_ask = QCheckBox(text["dont_ask"])
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(self.do_not_ask)
        buttons = QDialogButtonBox()
        start = buttons.addButton(text["start_guide"], QDialogButtonBox.AcceptRole)
        skip = buttons.addButton(text["not_now"], QDialogButtonBox.RejectRole)
        start.setDefault(True)
        start.clicked.connect(self.accept)
        skip.clicked.connect(self.reject)
        layout.addWidget(buttons)


class GuideOverlay(QWidget):
    """Phase-1 overlay foundation: dims the parent and exposes a target rectangle."""
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._target = QRect()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.hide()

    def set_target(self, widget: QWidget | None) -> None:
        if widget is None or not widget.isVisible():
            self._target = QRect()
        else:
            top_left = widget.mapTo(self.parentWidget(), widget.rect().topLeft())
            self._target = QRect(top_left, widget.size()).adjusted(-6, -6, 6, 6)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 20, 45, 110))
        if not self._target.isNull():
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self._target, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#0099E5"), 3))
            painter.drawRoundedRect(self._target, 8, 8)


class GuideViewer(QDialog):
    def __init__(self, manager: "GuideManager", steps: list[dict[str, Any]], parent: QWidget | None = None):
        super().__init__(parent)
        self.manager = manager
        self.steps = steps or DEFAULT_STEPS
        self.index = 0
        self.setWindowTitle(manager.text("guide"))
        self.setMinimumSize(680, 480)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        self.progress = QLabel()
        self.progress.setStyleSheet("color:#64748B; font-weight:bold;")
        self.title = QLabel()
        self.title.setFont(QFont("Arial", 20, QFont.Bold))
        self.title.setWordWrap(True)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMinimumHeight(150)
        self.image.setStyleSheet("background:#F1F5F9; border:1px solid #CBD5E1; border-radius:8px;")
        self.image.setText(manager.text("image_area"))
        self.never_again = QCheckBox(manager.text("never_show"))
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.body.setStyleSheet("font-size:15px; color:#1E293B; padding:12px 2px;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body_host = QWidget()
        body_layout = QVBoxLayout(body_host)
        body_layout.addWidget(self.body)
        body_layout.addStretch()
        scroll.setWidget(body_host)

        root.addWidget(self.progress)
        root.addWidget(self.title)
        root.addWidget(self.image)
        root.addWidget(scroll, 1)
        root.addWidget(self.never_again)

        nav = QHBoxLayout()
        self.previous = QPushButton(manager.text("previous"))
        self.jump = QPushButton(manager.text("go_to_section"))
        self.skip = QPushButton(manager.text("skip"))
        self.next = QPushButton(manager.text("next"))
        self.previous.clicked.connect(self.go_previous)
        self.jump.clicked.connect(self.jump_to_target)
        self.skip.clicked.connect(self.skip_guide)
        self.next.clicked.connect(self.go_next)
        nav.addWidget(self.previous)
        nav.addWidget(self.jump)
        nav.addStretch()
        nav.addWidget(self.skip)
        nav.addWidget(self.next)
        root.addLayout(nav)
        self.render_step()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Right, Qt.Key_Return, Qt.Key_Enter):
            self.go_next()
            return
        if event.key() == Qt.Key_Left:
            self.go_previous()
            return
        super().keyPressEvent(event)

    def render_step(self):
        step = self.steps[self.index]
        self.progress.setText(self.manager.text("progress").format(current=self.index + 1, total=len(self.steps)))
        self.title.setText(str(step.get("title", "")))
        self.body.setText(str(step.get("body", "")))
        self.previous.setEnabled(self.index > 0)
        self.next.setText(self.manager.text("finish") if self.index == len(self.steps) - 1 else self.manager.text("next"))
        image_name = str(step.get("image", "")).strip()
        image_path = self.manager.assets_dir / "images" / image_name if image_name else None
        if image_path and image_path.is_file():
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(str(image_path))
            self.image.setPixmap(pixmap.scaled(self.image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image.show()
        else:
            self.image.hide()
        self.manager.highlight_target(str(step.get("target", "")))

    def _show_action_error(self, exc: Exception) -> None:
        try:
            self.manager.log_action(f"Guide action failed: {exc!r}")
        except Exception:
            pass
        QMessageBox.critical(self, self.manager.text("guide_error_title"), f"{self.manager.text('guide_error_body')}\n\n{exc}")

    def skip_guide(self):
        try:
            self.manager.clear_highlight()
            self.reject()
        except Exception as exc:
            self._show_action_error(exc)

    def jump_to_target(self):
        try:
            step = self.steps[self.index]
            self.manager.navigate_to_target(str(step.get("target", "")))
        except Exception as exc:
            self._show_action_error(exc)

    def go_previous(self):
        try:
            if self.index > 0:
                self.index -= 1
                self.render_step()
        except Exception as exc:
            self._show_action_error(exc)

    def go_next(self):
        try:
            if self.index >= len(self.steps) - 1:
                self.manager.mark_completed(self.never_again.isChecked())
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Question)
                box.setWindowTitle(self.manager.text("complete_title"))
                box.setText(self.manager.text("complete_body"))
                yes_button = box.addButton(self.manager.text("yes"), QMessageBox.YesRole)
                box.addButton(self.manager.text("no"), QMessageBox.NoRole)
                box.setDefaultButton(yes_button)
                box.exec()
                create_now = box.clickedButton() is yes_button
                self.accept()
                if create_now:
                    QTimer.singleShot(0, lambda: self.manager.navigate_to_target("nav_complaint"))
                return
            self.index += 1
            self.render_step()
        except Exception as exc:
            self._show_action_error(exc)

    def done(self, result):
        self.manager.clear_highlight()
        super().done(result)


class ExitDialog(QDialog):
    def __init__(self, text: dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(text["exit_title"])
        self.setModal(True)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        title = QLabel(text["exit_title"])
        title.setFont(QFont("Arial", 17, QFont.Bold))
        body = QLabel(text["exit_body"])
        self.show_next = QCheckBox(text["show_next"])
        self.show_next.setChecked(False)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addSpacing(8)
        layout.addWidget(self.show_next)
        buttons = QDialogButtonBox()
        cancel = buttons.addButton(text["cancel"], QDialogButtonBox.RejectRole)
        exit_button = buttons.addButton(text["exit"], QDialogButtonBox.AcceptRole)
        cancel.clicked.connect(self.reject)
        exit_button.clicked.connect(self.accept)
        layout.addWidget(buttons)


class GuideManager:
    def __init__(self, main_window: QWidget, app_dir: Path, language: str = "en"):
        self.main_window = main_window
        self.app_dir = Path(app_dir)
        self.language = language if language in TRANSLATIONS else "en"
        self.settings_path = self.app_dir / "config" / "guide_settings.json"
        self.guides_dir = self.app_dir / "common_guide" / "guides"
        self.assets_dir = self.app_dir / "common_guide" / "assets"
        self.settings = dict(DEFAULT_SETTINGS)
        self.settings.update(_read_json(self.settings_path, {}))
        self.steps = self._load_steps()
        self.overlay = GuideOverlay(main_window)
        self.viewer: GuideViewer | None = None

    def text(self, key: str) -> str:
        return TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

    def set_language(self, language: str) -> None:
        self.language = language if language in TRANSLATIONS else "en"
        self.steps = self._load_steps()
        if self.viewer and self.viewer.isVisible():
            self.viewer.close()
            self.viewer = None

    def _load_steps(self) -> list[dict[str, Any]]:
        payload = _read_json(self.guides_dir / "complaint_steps.json", {})
        if not isinstance(payload, dict):
            return list(DEFAULT_STEPS)
        localized = payload.get("translations", {}).get(self.language)
        if not localized:
            localized = payload.get("translations", {}).get("en")
        steps = localized or payload.get("steps")
        return steps if isinstance(steps, list) and steps else list(DEFAULT_STEPS)

    def log_action(self, message: str) -> None:
        try:
            logger = getattr(self.main_window, "status", None)
            log_function = getattr(__import__("hub_app"), "log", None)
            if callable(log_function):
                log_function(message)
            elif logger is not None:
                logger.setText(message)
        except Exception:
            pass

    def save(self) -> None:
        _write_json(self.settings_path, self.settings)

    def should_prompt(self) -> bool:
        return bool(self.settings.get("show_guide_next_startup")) or (
            bool(self.settings.get("show_startup_prompt", True)) and not bool(self.settings.get("do_not_ask_again", False))
        )

    def show_startup_prompt(self) -> None:
        if not self.should_prompt():
            return
        dialog = WelcomeDialog(TRANSLATIONS.get(self.language, TRANSLATIONS["en"]), self.main_window)
        accepted = dialog.exec() == QDialog.Accepted
        if dialog.do_not_ask.isChecked():
            self.settings["do_not_ask_again"] = True
            self.settings["show_startup_prompt"] = False
        self.settings["show_guide_next_startup"] = False
        self.save()
        if accepted:
            self.show_guide()

    def show_guide(self) -> None:
        if self.viewer and self.viewer.isVisible():
            self.viewer.raise_()
            self.viewer.activateWindow()
            return
        self.viewer = GuideViewer(self, self.steps, self.main_window)
        self.viewer.show()
        self.viewer.raise_()

    def highlight_target(self, name: str) -> None:
        target = None
        if name:
            target = getattr(self.main_window, name, None)
            if target is None and name == "nav_complaint":
                for key, button in getattr(self.main_window, "nav_buttons", []):
                    if key == "complaint":
                        target = button
                        break
        self.overlay.setGeometry(self.main_window.rect())
        self.overlay.set_target(target)
        if target is not None:
            self.overlay.show()
            self.overlay.raise_()
            if self.viewer:
                self.viewer.raise_()
        else:
            self.overlay.hide()

    def clear_highlight(self) -> None:
        self.overlay.hide()

    def navigate_to_target(self, name: str) -> None:
        if name == "nav_complaint" and hasattr(self.main_window, "open_tool"):
            self.clear_highlight(); self.main_window.open_tool("complaint")
            return
        target = getattr(self.main_window, name, None)
        if target is not None:
            target.setFocus()

    def mark_completed(self, never_again: bool = False) -> None:
        self.settings["last_completed_guide_version"] = self.settings.get("guide_version", "1.0")
        self.settings["show_guide_next_startup"] = False
        if never_again:
            self.settings["do_not_ask_again"] = True
            self.settings["show_startup_prompt"] = False
        self.save()

    def reset_for_next_startup(self) -> None:
        self.settings["show_guide_next_startup"] = True
        self.save()

    def confirm_exit(self) -> tuple[bool, bool]:
        dialog = ExitDialog(TRANSLATIONS.get(self.language, TRANSLATIONS["en"]), self.main_window)
        accepted = dialog.exec() == QDialog.Accepted
        return accepted, dialog.show_next.isChecked()
