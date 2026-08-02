from __future__ import annotations
import sys, os, json, zipfile, shutil, datetime, re, platform, subprocess, time
from pathlib import Path
from feedback_engine import FeedbackEngine, FeedbackRequest, build_runtime_context
from common_guide import GuideManager
from common_validation import ValidationManager

try:
    from PySide6.QtCore import Qt, QSize, QDate, QLocale, QThread, Signal, QTimer
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
        QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QMessageBox, QFileDialog,
        QDialog, QLineEdit, QFormLayout, QScrollArea, QTextEdit,
        QTableWidget, QTableWidgetItem, QTabWidget, QCheckBox, QListWidget,
        QStyle, QDialogButtonBox,
        QListWidgetItem, QGroupBox, QProgressBar, QDateEdit, QCalendarWidget, QHeaderView, QInputDialog, QToolButton
    )
except Exception as e:
    print('PySide6 is required. Install with: pip install PySide6')
    raise

APP_DIR = Path(__file__).resolve().parent

LANG_NAMES = {
    'en':'English', 'ja':'日本語', 'ko':'한국어', 'th':'ไทย',
    'zh-TW':'繁體中文', 'zh-CN':'简体中文', 'hi':'हिन्दी'
}
COUNTRY_DEFAULT_LANG = {
    'Japan':'ja', 'Korea':'ko', 'Thailand':'th', 'Philippines':'en',
    'Taiwan':'zh-TW', 'China':'zh-CN', 'India':'hi', 'Australia':'en',
    'Vietnam':'en'
}

PRIMARY = '#005DAA'
DARK = '#052A4F'
ACCENT = '#0099E5'
BG = '#F5F8FC'
CARD_BORDER = '#D7E3F1'


class CurrentMonthCalendar(QCalendarWidget):
    """Calendar popup that opens on the current month without forcing a date value."""
    def showEvent(self, event):
        today = QDate.currentDate()
        self.setCurrentPage(today.year(), today.month())
        super().showEvent(event)

DISTRIBUTOR_DISPLAY = {
    'GEMS': 'GEMS',
    'Vattikuti': 'Vattikuti',
    'Device Technologies': 'Device Technology',
    'Device Technologies Asia': 'Device Technology Asia',
    'Fosun InSightec': 'Fosun InSightec',
    'ProChime': 'ProChime',
}
DISTRIBUTOR_ORG_BY_DISPLAY = {v: k for k, v in DISTRIBUTOR_DISPLAY.items()}

def distributor_display_name(organization: str) -> str:
    return DISTRIBUTOR_DISPLAY.get(organization, organization)

def selected_company_org(display_name: str) -> str:
    return DISTRIBUTOR_ORG_BY_DISPLAY.get(display_name, display_name)


def _scope_values(person: dict, *keys: str) -> set[str]:
    """Read a person scope field as a normalized set without company-name assumptions."""
    values: set[str] = set()
    for key in keys:
        raw = person.get(key)
        if isinstance(raw, (list, tuple, set)):
            candidates = raw
        elif isinstance(raw, str):
            candidates = re.split(r'[;,|\n]+', raw)
        elif raw is None:
            candidates = []
        else:
            candidates = [raw]
        values.update(str(v).strip() for v in candidates if str(v).strip())
    return values


def person_from_settings(settings: dict, people: list[dict]) -> dict:
    """Resolve the effective logged-in person, including a shared-user actual user."""
    company_display = settings.get('company', '')
    name = settings.get('actual_user') or settings.get('user') or ''
    if company_display == 'InSightec':
        return next((p for p in people
                     if p.get('company') == 'InSightec' and p.get('name') == name), {})
    organization = selected_company_org(company_display)
    return next((p for p in people
                 if p.get('company') == 'Distributor'
                 and p.get('organization') == organization
                 and p.get('name') == name), {})


def company_site_filter(company_display: str, rows: list[dict], person: dict | None = None) -> list[dict]:
    """Limit non-InSightec users to the areas explicitly assigned in People master.

    Supported data-driven scope fields are assigned_sites/sites/site_scope and
    assigned_countries/countries/country. No distributor-to-country mapping is used.
    An empty distributor scope intentionally returns no sites (secure default).
    """
    if company_display == 'InSightec':
        return list(rows)

    person = person or {}
    sites = _scope_values(person, 'assigned_sites', 'sites', 'site_scope')
    countries = _scope_values(person, 'assigned_countries', 'countries', 'country')
    if not sites and not countries:
        return []

    matched = []
    for row in rows:
        hospital = str(row.get('hospital_name', '')).strip()
        serial = str(row.get('serial', '')).strip()
        country = str(row.get('country', '')).strip()
        if sites and (hospital in sites or serial in sites):
            matched.append(row)
        elif countries and country in countries:
            matched.append(row)
    return matched


def read_json(path: Path, default):
    try:
        if path.exists():
            return json.load(open(path, encoding='utf-8'))
    except Exception:
        pass
    return default

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def log(msg: str):
    p = APP_DIR / 'logs' / 'hub.log'
    p.parent.mkdir(exist_ok=True)
    with p.open('a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")

_TRANSLATIONS_CACHE = None

class MasterDataLoader(QThread):
    loaded = Signal(dict)
    failed = Signal(str)
    def run(self):
        try:
            names = ('hospital_master.json','people_master.json','recipients.json','complaint_field_options.json','translations.json')
            payload = {name: read_json(APP_DIR/'masters'/name, [] if name.endswith('master.json') else {}) for name in names}
            self.loaded.emit(payload)
        except Exception as exc:
            self.failed.emit(f'{type(exc).__name__}: {exc}')

def outlook_process_running() -> bool:
    if not sys.platform.startswith('win'):
        return False
    try:
        result = subprocess.run(['tasklist','/FI','IMAGENAME eq OUTLOOK.EXE'], capture_output=True, text=True, timeout=4, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return 'OUTLOOK.EXE' in (result.stdout or '').upper()
    except Exception:
        return False

def default_mail_app_name() -> str:
    if not sys.platform.startswith('win'):
        return ''
    try:
        import winreg
        path = r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\mailto\UserChoice'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            progid, _ = winreg.QueryValueEx(key, 'ProgId')
        return str(progid)
    except Exception:
        return ''


def find_classic_outlook_executable() -> str:
    """Locate Classic Outlook without assuming a fixed Office installation path."""
    if not sys.platform.startswith('win'):
        return ''
    candidates = []
    try:
        import winreg
        registry_locations = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE'),
        ]
        for hive, key_path in registry_locations:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if value:
                        candidates.append(str(value).strip('\"'))
            except OSError:
                pass
    except Exception:
        pass
    found = shutil.which('outlook.exe') or shutil.which('OUTLOOK.EXE')
    if found:
        candidates.append(found)
    for env_name in ('ProgramFiles', 'ProgramFiles(x86)'):
        root = os.environ.get(env_name)
        if root:
            office_root = Path(root) / 'Microsoft Office'
            for relative in (('root','Office16'), ('root','Office15'), ('Office16',), ('Office15',)):
                candidates.append(str(office_root.joinpath(*relative) / 'OUTLOOK.EXE'))
    for candidate in candidates:
        try:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate))
        except Exception:
            pass
    return ''

def ui_text(widget, key):
    """Return translated UI text using the nearest settings owner."""
    global _TRANSLATIONS_CACHE
    if _TRANSLATIONS_CACHE is None:
        _TRANSLATIONS_CACHE = read_json(APP_DIR/'masters/translations.json', {})
    current = widget
    settings = None
    while current is not None:
        settings = getattr(current, 'settings', None)
        if isinstance(settings, dict):
            break
        try:
            current = current.parent()
        except Exception:
            current = None
    if not isinstance(settings, dict):
        settings = read_json(APP_DIR/'config/settings.json', {})
    lang = settings.get('language', 'en')
    table = _TRANSLATIONS_CACHE.get(lang, _TRANSLATIONS_CACHE.get('en', {}))
    return table.get(key, _TRANSLATIONS_CACHE.get('en', {}).get(key, key))

def contains_non_english_text(text: str) -> bool:
    """Return True when alphabetic characters outside ASCII English are present."""
    for ch in text or "":
        if ch.isalpha() and not ("A" <= ch <= "Z" or "a" <= ch <= "z"):
            return True
    return False

class StartupDialog(QDialog):
    def __init__(self, settings, people):
        super().__init__()
        self.setWindowTitle(ui_text(self, 'startup_selection'))
        self.setModal(True)
        self.settings = settings
        self.people = people
        self.setMinimumWidth(560)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        self.setStyleSheet('QLabel{font-size:14px;} QLineEdit,QComboBox{font-size:14px; min-height:34px; padding:4px 7px;} QPushButton{font-size:14px; min-height:34px;}')
        title = QLabel('InSightec Complaint Service Hub')
        title.setFont(QFont('Arial', 21, QFont.Bold))
        title.setStyleSheet(f'color:{PRIMARY};')
        layout.addWidget(title)
        form = QFormLayout()
        self.company = QComboBox()
        # Keep the first dialog simple: internal users or distributor field engineers.
        
        distributor_names = sorted({
            distributor_display_name(p.get('organization','')) for p in self.people
            if p.get('company') == 'Distributor'
            and p.get('active', True)
            and (p.get('role') == 'Distributor FE' or p.get('login_enabled', False))
            and p.get('organization') and p.get('organization') != 'Distributor'
        })
        self.company.addItems(['InSightec'] + distributor_names)
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password); self.password.setPlaceholderText(ui_text(self, 'optional_admin_password'))
        self.user = QComboBox()
        self.actual_user = QComboBox(); self.actual_user.setEnabled(False)
        form.addRow(ui_text(self, 'company'), self.company)
        form.addRow(ui_text(self, 'password'), self.password)
        form.addRow(ui_text(self, 'user'), self.user)
        form.addRow(ui_text(self, 'actual_user_shared'), self.actual_user)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_checked)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.company.currentTextChanged.connect(self.refresh_users)
        if settings.get('company'):
            i=self.company.findText(settings.get('company'))
            if i>=0: self.company.setCurrentIndex(i)
        self.refresh_users()
        if settings.get('user'):
            i=self.user.findText(settings.get('user'))
            if i>=0: self.user.setCurrentIndex(i)
        self.user.currentTextChanged.connect(self.refresh_actual)
        self.refresh_actual()

    def refresh_users(self):
        comp = self.company.currentText()
        self.password.setEnabled(comp == 'InSightec')
        self.user.clear()
        if comp != 'InSightec':
            selected_org = selected_company_org(comp)
            users = [
                p.get('name','') for p in self.people
                if p.get('company') == 'Distributor'
                and p.get('organization') == selected_org
                and (p.get('role') == 'Distributor FE' or p.get('login_enabled', False))
                and p.get('active', True)
            ]
        else:
            users = [
                p.get('name','') for p in self.people
                if p.get('company') == 'InSightec'
                and p.get('active', True)
            ]
        if not users:
            users = ['Shared User']
        self.user.addItems(users)
        self.refresh_actual()

    def refresh_actual(self):
        name = self.user.currentText()
        shared = 'shared' in name.lower() or '共用' in name
        self.actual_user.setEnabled(shared)
        self.actual_user.clear()
        if shared:
            comp = self.company.currentText()
            if comp != 'InSightec':
                selected_org = selected_company_org(comp)
                names = [
                    p.get('name','') for p in self.people
                    if p.get('company') == 'Distributor'
                    and p.get('organization') == selected_org
                    and (p.get('role') == 'Distributor FE' or p.get('login_enabled', False))
                    and p.get('active', True)
                    and 'shared' not in p.get('name','').lower()
                ]
            else:
                names = [
                    p.get('name','') for p in self.people
                    if p.get('company') == 'InSightec'
                    and 'shared' not in p.get('name','').lower()
                ]
            self.actual_user.addItems(names or [''])

    def accept_checked(self):
        if self.company.currentText() == 'InSightec':
            entered_password = self.password.text().strip()
            if entered_password and entered_password != '5963':
                QMessageBox.warning(self, ui_text(self,'password'), ui_text(self,'password_required'))
                return
            self.settings['startup_admin'] = (entered_password == '5963')
        else:
            self.settings['startup_admin'] = False
        if self.actual_user.isEnabled() and not self.actual_user.currentText().strip():
            QMessageBox.warning(self, ui_text(self,'actual_user'), ui_text(self,'select_actual_user'))
            return
        self.settings['company'] = self.company.currentText()
        self.settings['user'] = self.user.currentText()
        self.settings['actual_user'] = self.actual_user.currentText() if self.actual_user.isEnabled() else ''
        if not self.settings.get('language') or self.settings.get('language') == 'auto':
            country = self.selected_person().get('country','')
            self.settings['language'] = COUNTRY_DEFAULT_LANG.get(country, 'en')
        self.accept()

    def selected_person(self):
        name = self.user.currentText()
        
        selected = self.company.currentText()
        if selected == 'InSightec':
            return next((p for p in self.people if p.get('name') == name and p.get('company') == 'InSightec'), {})
        selected_org = selected_company_org(selected)
        return next((p for p in self.people if p.get('name') == name and p.get('company') == 'Distributor' and p.get('organization') == selected_org), {})

class ToolCard(QFrame):
    def __init__(self, title, desc, icon, color, tag, callback, start_text='Start'):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(170)
        self.setCursor(Qt.PointingHandCursor)
        self._callback = callback
        self.setStyleSheet(f'''
            QFrame {{ background:white; border:1px solid {CARD_BORDER}; border-radius:14px; }}
            QLabel {{ border:0; background:transparent; }}
            QPushButton {{ background:{color}; color:white; border:0; border-radius:7px; padding:8px 16px; font-weight:bold; }}
            QPushButton:hover {{ background:{PRIMARY}; }}
        ''')
        lay = QVBoxLayout(self); lay.setContentsMargins(20,16,20,16); lay.setSpacing(8)
        header=QHBoxLayout()
        icon_l=QLabel(icon); icon_l.setFont(QFont('Arial',22)); icon_l.setStyleSheet(f'color:{color};')
        title_l=QLabel(title); title_l.setFont(QFont('Arial',16,QFont.Bold)); title_l.setStyleSheet(f'color:{color};')
        header.addWidget(icon_l); header.addWidget(title_l); header.addStretch()
        lay.addLayout(header)
        d=QLabel(desc); d.setWordWrap(True); d.setMinimumHeight(44); d.setStyleSheet('color:#27313D;')
        lay.addWidget(d)
        tag_l=QLabel(tag); tag_l.setStyleSheet('background:#EDF3FA; color:#123B66; border-radius:6px; padding:4px 8px; font-weight:bold;')
        lay.addWidget(tag_l, alignment=Qt.AlignLeft)
        lay.addStretch()
        btn=QPushButton(start_text + '  ›'); btn.setMinimumHeight(34)
        # QPushButton.clicked emits a boolean. Do not pass it to the tool callback,
        # otherwise it replaces the captured tool key and open_tool(False) is called.
        btn.clicked.connect(lambda checked=False: self.activate())
        lay.addWidget(btn)

    def activate(self):
        try:
            self._callback()
        except Exception as exc:
            log(f'Tool card activation failed: {exc!r}')
            QMessageBox.critical(self, ui_text(self,'launch_error'), ui_text(self,'function_start_failed') + f'\n\n{exc}')

    def mousePressEvent(self, event):
        # Make the entire card clickable, not only the Start button.
        if event.button() == Qt.LeftButton:
            self.activate()
            event.accept()
            return
        super().mousePressEvent(event)

class ComplaintDialog(QDialog):
    """Guided complaint entry prototype."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = getattr(parent, 'settings', read_json(APP_DIR/'config/settings.json', {}))
        self.setWindowTitle(ui_text(self, 'complaint_tool'))
        self.resize(1050, 760)
        self.setMinimumSize(760, 580)
        cache = getattr(parent, 'master_cache', {}) if parent is not None else {}
        self.hospital_master_all = cache.get('hospital_master.json') or read_json(APP_DIR/'masters/hospital_master.json', [])
        self.people_master = cache.get('people_master.json') or read_json(APP_DIR/'masters/people_master.json', [])
        self.logged_in_person = person_from_settings(self.settings, self.people_master)
        self.hospital_master = company_site_filter(
            self.settings.get('company', 'InSightec'),
            self.hospital_master_all,
            self.logged_in_person,
        )
        self.recipient_master = cache.get('recipients.json') or read_json(APP_DIR/'masters/recipients.json', {})
        self.option_path = APP_DIR/'masters/complaint_field_options.json'
        self.field_options = cache.get('complaint_field_options.json') or read_json(self.option_path, {})
        self.admin_mode = bool(getattr(parent, 'admin_mode', self.settings.get('startup_admin', False)))
        self.complaint_attachments = []
        self._syncing_site_fields = False
        self.required_widgets = {}
        self.required_sections = {}
        self.validation_manager = ValidationManager(self, self._widget_text)
        self.validation_manager.changed.connect(self._apply_validation_result)
        self.all_editors = []
        # Lazy-loaded Investigation and Closure widgets must still have safe
        # placeholders. Preview, English validation and Outlook generation can
        # run before those tabs are opened. Without these placeholders, Qt slot
        # callbacks raise AttributeError and appear to do nothing in console-free builds.
        for _name in (
            'classification', 'criticality', 'complaint_type', 'sub_type',
            'investigation_summary', 'root_cause', 'capa_required', 'capa_reason',
            'final_conclusion', 'close_as', 'completed_date', 'final_reply',
            'required_action', 'action_description', 'responsible_person', 'target_due_date'
        ):
            setattr(self, _name, None)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel(ui_text(self, 'new_complaint_medical_device'))
        title.setFont(QFont('Arial', 21, QFont.Bold))
        title.setStyleSheet(f'color:{DARK};')
        header.addWidget(title); header.addStretch()
        self.readiness = QLabel(ui_text(self, 'not_ready'))
        header.addWidget(self.readiness)
        root.addLayout(header)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0)
        self.progress.setFormat(ui_text(self, 'completion') + ': %p%')
        self.progress.setMinimumHeight(20)
        progress_row.addWidget(self.progress, 1)
        self.issue_count = QLabel('')
        progress_row.addWidget(self.issue_count)
        root.addLayout(progress_row)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #D7E3F1; background:white; border-radius:8px; }
            QTabBar::tab { padding:10px 18px; margin-right:2px; background:#EAF2FA; color:#23415D; }
            QTabBar::tab:selected { background:#005DAA; color:white; font-weight:bold; }
        """)
        root.addWidget(self.tabs, 1)
        self._lazy_tabs_built = set()
        self._build_basic_tab(); self._build_medical_tab(); self._add_lazy_tab('Investigation', 'investigation'); self._add_lazy_tab('Closure', 'closure')
        self._build_additional_tab(); self._add_lazy_tab(ui_text(self,'preview'), 'preview')
        self._disable_intake_only_tabs()

        nav = QHBoxLayout()
        self.prev_btn = QPushButton('‹ ' + ui_text(self, 'previous'))
        self.next_btn = QPushButton(ui_text(self, 'next') + ' ›')
        self.prev_btn.clicked.connect(lambda: self._move_tab(-1))
        self.next_btn.clicked.connect(lambda: self._move_tab(1))
        nav.addWidget(self.prev_btn); nav.addWidget(self.next_btn); nav.addStretch()
        cancel = QPushButton(ui_text(self, 'cancel')); cancel.clicked.connect(self.reject)
        save_new = QPushButton(ui_text(self, 'save_and_new')); save_new.clicked.connect(self.save_and_new)
        save = QPushButton(ui_text(self, 'save')); save.setStyleSheet(f'background:{PRIMARY}; color:white; font-weight:bold; padding:8px 20px; border-radius:6px;'); save.clicked.connect(self.save_record)
        nav.addWidget(cancel); nav.addWidget(save_new); nav.addWidget(save)
        root.addLayout(nav)

        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.country.currentTextChanged.connect(self.on_country_changed)
        self.hospital.currentTextChanged.connect(self.on_hospital_changed)
        self.model.currentTextChanged.connect(self.on_model_changed)
        self.serial.currentTextChanged.connect(self.on_serial_changed)
        self.populate_company_sites(); self.update_recipient_field(); self._connect_validation(); self.update_status(); self.on_tab_changed(0)

    def _add_lazy_tab(self, title, key):
        page = QWidget(); page.setProperty('lazy_key', key)
        lay = QVBoxLayout(page); label = QLabel('This section will load when selected.'); label.setAlignment(Qt.AlignCenter); lay.addWidget(label)
        self.tabs.addTab(page, title)

    def _ensure_lazy_tab(self, index):
        page = self.tabs.widget(index)
        key = page.property('lazy_key') if page else None
        if not key or key in self._lazy_tabs_built:
            return
        title = self.tabs.tabText(index)
        self.tabs.removeTab(index); page.deleteLater()
        if key == 'investigation': self._build_investigation_tab()
        elif key == 'closure': self._build_closure_tab()
        elif key == 'preview': self._build_preview_tab()
        new_index = self.tabs.count()-1
        self.tabs.tabBar().moveTab(new_index, index)
        self.tabs.setCurrentIndex(index)
        self._lazy_tabs_built.add(key)

    def _card(self, title_text):
        box = QGroupBox(title_text)
        box.setStyleSheet("QGroupBox {font-weight:bold; color:#123B66; border:1px solid #D7E3F1; border-radius:8px; margin-top:12px; padding-top:10px;} QGroupBox::title {subcontrol-origin:margin; left:12px; padding:0 5px;}")
        form = QFormLayout(box); form.setLabelAlignment(Qt.AlignLeft); form.setFormAlignment(Qt.AlignTop); form.setHorizontalSpacing(18); form.setVerticalSpacing(10)
        return box, form

    def _line(self, placeholder=''):
        w=QLineEdit(); w.setPlaceholderText(placeholder); self.all_editors.append(w); return w

    def _combo(self, items=None, editable=True):
        w=QComboBox(); w.setEditable(editable); w.setInsertPolicy(QComboBox.NoInsert)
        if items: w.addItems(items)
        self.all_editors.append(w); return w

    def _option_combo(self, key, defaults):
        items = self.field_options.get(key, defaults)
        if not isinstance(items, list) or not items:
            items = defaults
        w = self._combo([str(x) for x in items], True)
        w.setProperty('option_key', key)
        return w

    def edit_input_lists(self):
        if not self.admin_mode:
            QMessageBox.warning(self, 'Admin Mode', 'Admin Mode is required to edit input lists.')
            return
        dlg=QDialog(self); dlg.setWindowTitle('Complaint Input List Manager'); dlg.resize(760,620)
        lay=QVBoxLayout(dlg)
        info=QLabel('Edit JSON lists below. Each field must contain an array of selectable values. Manual entry remains available to all users.')
        info.setWordWrap(True); lay.addWidget(info)
        editor=QTextEdit(); editor.setPlainText(json.dumps(self.field_options, ensure_ascii=False, indent=2)); lay.addWidget(editor,1)
        row=QHBoxLayout(); reset=QPushButton('Load current defaults'); save=QPushButton('Save lists'); cancel=QPushButton('Cancel')
        row.addWidget(reset); row.addStretch(); row.addWidget(cancel); row.addWidget(save); lay.addLayout(row)
        reset.clicked.connect(lambda: editor.setPlainText(json.dumps(self._current_option_lists(), ensure_ascii=False, indent=2)))
        cancel.clicked.connect(dlg.reject)
        def do_save():
            try:
                data=json.loads(editor.toPlainText())
                if not isinstance(data, dict) or any(not isinstance(v,list) for v in data.values()):
                    raise ValueError('Root must be an object and every value must be a list.')
                write_json(self.option_path, data); self.field_options=data
                QMessageBox.information(dlg,'Saved','Input lists were saved. They will be fully applied when the Complaint window is reopened.')
                dlg.accept()
            except Exception as exc:
                QMessageBox.critical(dlg,'Invalid list data',str(exc))
        save.clicked.connect(do_save); dlg.exec()

    def _current_option_lists(self):
        result={}
        for w in self.all_editors:
            if isinstance(w,QComboBox) and w.property('option_key'):
                result[str(w.property('option_key'))]=[w.itemText(i) for i in range(w.count())]
        return result

    def _text(self, height=95):
        w=QTextEdit(); w.setMinimumHeight(height); self.all_editors.append(w); return w

    def _configure_calendar_popup(self, date_edit):
        """Use a consistent English calendar with a visible year and Today shortcut."""
        calendar = CurrentMonthCalendar(date_edit)
        calendar.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        calendar.setNavigationBarVisible(True)
        calendar.setGridVisible(False)
        calendar.setMinimumWidth(390)
        calendar.setMinimumHeight(300)
        calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        calendar.setDateEditEnabled(True)
        calendar.setCurrentPage(QDate.currentDate().year(), QDate.currentDate().month())
        calendar.setStyleSheet(
            'QCalendarWidget QWidget#qt_calendar_navigationbar { min-height: 42px; }'
            'QCalendarWidget QToolButton { font-size: 14px; font-weight: 600; min-height: 34px; }'
            'QCalendarWidget QToolButton#qt_calendar_monthbutton { min-width: 135px; }'
            'QCalendarWidget QToolButton#qt_calendar_yearbutton { min-width: 82px; }'
            'QCalendarWidget QAbstractItemView { font-size: 14px; }'
        )
        month_button = calendar.findChild(QToolButton, 'qt_calendar_monthbutton')
        year_button = calendar.findChild(QToolButton, 'qt_calendar_yearbutton')
        if month_button is not None:
            month_button.setMinimumWidth(135)
        if year_button is not None:
            year_button.setMinimumWidth(82)

        today_button = QPushButton('Today', calendar)
        today_button.setObjectName('calendarTodayButton')
        today_button.setMinimumHeight(34)
        today_button.setToolTip('Select today')
        layout = calendar.layout()
        if isinstance(layout, QGridLayout):
            # QGridLayout supports rowCount/columnCount and positional addWidget.
            layout.addWidget(today_button, layout.rowCount(), 0, 1, max(1, layout.columnCount()))
        elif layout is not None:
            # Qt currently exposes QCalendarWidget's internal layout as a
            # QVBoxLayout on some PySide6 versions. Box layouts do not have
            # rowCount()/columnCount(); append the button safely instead.
            layout.addWidget(today_button)
        else:
            # Defensive fallback for unexpected Qt platform implementations.
            today_button.setParent(calendar)
            today_button.move(12, max(0, calendar.height() - today_button.sizeHint().height() - 8))
            today_button.show()

        def select_today():
            today = QDate.currentDate()
            calendar.setSelectedDate(today)
            calendar.showSelectedDate()
            date_edit.setDate(today)
            calendar.hide()

        today_button.clicked.connect(select_today)
        date_edit.setCalendarWidget(calendar)
        date_edit._calendar_today_button = today_button
        return calendar

    def _date(self, default_today=False):
        w = QDateEdit()
        w.setCalendarPopup(True)
        w.setDisplayFormat('yyyy-MM-dd')
        w.setMinimumDate(QDate(1900, 1, 1))
        w.setSpecialValueText('--None--')
        w.setDate(QDate.currentDate() if default_today else w.minimumDate())
        self._configure_calendar_popup(w)
        self.all_editors.append(w)
        return w

    def _required(self, key, label, widget, section='basic'):
        self.required_widgets[key] = (label, widget)
        self.required_sections[key] = section
        self.validation_manager.register(key, label, widget, section)
        widget.setToolTip(ui_text(self,'required_field'))
        return '* ' + label

    def _two_column_page(self):
        # A scroll-backed page prevents clipped controls on High-DPI and laptop screens.
        page=QScrollArea(); page.setWidgetResizable(True); page.setFrameShape(QFrame.NoFrame)
        body=QWidget(); outer=QHBoxLayout(body); outer.setContentsMargins(14,14,14,14); outer.setSpacing(14)
        left=QVBoxLayout(); right=QVBoxLayout(); outer.addLayout(left,1); outer.addLayout(right,1)
        left.addStretch(); right.addStretch(); page.setWidget(body)
        return page,left,right

    def _disable_intake_only_tabs(self):
        # Investigation and Closure are post-intake workflows. Keep their data model
        # for compatibility, but make the tabs visibly unavailable during new entry.
        for index in (2, 3):
            if index < self.tabs.count():
                self.tabs.setTabEnabled(index, False)
                self.tabs.setTabToolTip(index, 'Available after the complaint has been created.')
        self.tabs.tabBar().setStyleSheet(
            'QTabBar::tab:disabled { background:#D6DCE3; color:#7A8794; }'
        )

    def _move_tab(self, direction):
        index=self.tabs.currentIndex()+direction
        while 0 <= index < self.tabs.count() and not self.tabs.isTabEnabled(index):
            index += direction
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _build_basic_tab(self):
        page,left,right=self._two_column_page(); g,f=self._card(ui_text(self,'intake'))
        self.subject=self._line(ui_text(self,'english_only'))
        self.date_reported=self._date(default_today=True)
        self.country=self._combo(sorted({h.get('country','') for h in self.hospital_master if h.get('country')}))
        self.hospital=self._combo(editable=True); self.serial=self._combo(editable=True); self.sw=self._option_combo('software_version', ['4.25','4.26','6.24','6.26','6.32','6.5','6.52','6.58','7.0','7.32','7.33','7.41','7.42','7.43','7.44','7.45','8.0','8.1','9.0','9.01','No Relevant'])
        self.sw.setCurrentText('7.33')
        f.addRow(self._required('subject',ui_text(self,'complaint_subject'),self.subject),self.subject)
        f.addRow(self._required('date_reported',ui_text(self,'date_reported'),self.date_reported),self.date_reported)
        f.addRow(ui_text(self,'country'),self.country); f.addRow(ui_text(self,'hospital_name'),self.hospital)
        f.addRow(self._required('serial',ui_text(self,'serial_number'),self.serial),self.serial); left.insertWidget(0,g)
        g2,f2=self._card(ui_text(self,'system_information'))
        self.complaint_number=self._line(); self.event_date=self._date()
        self.product=self._combo(['Exablate Neuro','Exablate Body','Other'], True)
        self.model=self._combo(['650'], editable=True); self.model.setCurrentText('650'); self.business_unit=self._combo(['--None--','General','Archive','Restricted']); self.business_unit.setCurrentText('General')
        # MR information is populated from the selected system master.
        # referenced self.mr_info without creating it, causing Complaint/MR info startup errors.
        self.mr_info=self._line(); self.mr_info.setReadOnly(True)
        self.mr_info.setPlaceholderText('MR company / field strength / MR product')
        self.owner=self._line(); self.owner.setText(self.settings.get('actual_user') or self.settings.get('user',''))
        # Internal linked FE value used for export/recipient logic; not shown in the intake UI.
        self.distributor_fe=self._line(); self.distributor_fe.setReadOnly(True); self.distributor_fe.hide()
        f2.addRow(ui_text(self,'complaint_number'),self.complaint_number)
        f2.addRow(self._required('event_date',ui_text(self,'event_date'),self.event_date),self.event_date)
        f2.addRow(ui_text(self,'software_version'),self.sw); f2.addRow(ui_text(self,'product'),self.product)
        f2.addRow(ui_text(self,'model'),self.model); f2.addRow(ui_text(self,'mr_info'),self.mr_info)
        f2.addRow(self._required('business_unit',ui_text(self,'business_unit'),self.business_unit),self.business_unit); f2.addRow(ui_text(self,'owner'),self.owner); right.insertWidget(0,g2)
        self.tabs.addTab(page,ui_text(self,'basic'))

    def _build_medical_tab(self):
        page,left,right=self._two_column_page(); g,f=self._card(ui_text(self,'treatment_information'))
        self.usage_type=self._option_combo('usage_type', ['--None--','Clinical Research','Commercial','Pre-Clinical','Off Label','Site Initiated Clinical Research'])
        self.treatment_indication=self._option_combo('treatment_indication', ['--None--','Essential Tremor','Bilateral Essential Tremor',"Tremor Dominant Idiopathic Parkinson's Disease-Unilateral","Parkinson's Disease",'Neuropathic Pain','Prostate Cancer','Ablation of Prostate Tissue','Uterine Fibroids'])
        self.treatment_application=self._option_combo('treatment_application', ['--None--','UF','Bone','CBS','Prostate','Neuro 650','Neuro 220','Breast'])
        self.affected_treatment=self._option_combo('affected_treatment', ['--None--','Yes','No','Unknown'])
        self.usage_type.setCurrentText('Commercial')
        self.treatment_indication.setCurrentText('Essential Tremor')
        self.treatment_application.setCurrentText('Neuro 650')
        self.affected_treatment.setCurrentText('No')
        self.next_treatment=self._date()
        f.addRow(self._required('usage_type',ui_text(self,'usage_type'),self.usage_type,'medical'),self.usage_type)
        f.addRow(self._required('treatment_indication',ui_text(self,'treatment_indication'),self.treatment_indication,'medical'),self.treatment_indication)
        f.addRow(self._required('treatment_application',ui_text(self,'treatment_application'),self.treatment_application,'medical'),self.treatment_application)
        f.addRow(self._required('affected_treatment',ui_text(self,'affected_treatment'),self.affected_treatment,'medical'),self.affected_treatment)
        f.addRow(ui_text(self,'next_scheduled_treatment'),self.next_treatment); left.insertWidget(0,g)
        g2,f2=self._card(ui_text(self,'adverse_event_information'))
        self.adverse_occurred=self._option_combo('adverse_occurred', ['--None--','Yes','No']); self.adverse_type=self._option_combo('adverse_type', ['--None--','Serious','Non-serious','Unknown'])
        self.adverse_occurred.setCurrentText('No'); self.adverse_type.setCurrentText('--None--')
        self.symptom=self._text(105); self.initial_awareness=self._date(); self.supplemental_awareness=self._date()
        self.received_mode=self._option_combo('received_mode', ['--None--','Telephone','Mail','Email','Fax'])
        self.complaint_source=self._option_combo('complaint_source', ['--None--','Medical Staff','Pharmacist','Patient','Study Subject','Other','Customer','Distributor/Importer'])
        f2.addRow(self._required('adverse_occurred',ui_text(self,'adverse_event_occurred'),self.adverse_occurred,'medical'),self.adverse_occurred)
        f2.addRow(ui_text(self,'adverse_event_type'),self.adverse_type); f2.addRow(ui_text(self,'symptom'),self.symptom)
        f2.addRow(ui_text(self,'initial_awareness_date'),self.initial_awareness); f2.addRow(ui_text(self,'supplemental_awareness_date'),self.supplemental_awareness)
        f2.addRow(ui_text(self,'received_mode'),self.received_mode); f2.addRow(ui_text(self,'complaint_source'),self.complaint_source); right.insertWidget(0,g2)
        self.tabs.addTab(page,ui_text(self,'medical'))

    def _build_investigation_tab(self):
        page,left,right=self._two_column_page(); g,f=self._card(ui_text(self,'complaint_classification_risk'))
        self.classification=self._combo(['--None--','Product Complaint','Clinical Complaint','Service Complaint','Other'])
        self.criticality=self._combo(['--None--','Low','Medium','High','Critical'])
        self.complaint_type=self._combo(['--None--','Hardware','Software','Clinical','Usability','Other'])
        self.sub_type=self._combo(['--None--','Intermittent','Reproducible','Unknown','Other'])
        f.addRow(ui_text(self,'classification'),self.classification); f.addRow(ui_text(self,'criticality'),self.criticality)
        f.addRow(ui_text(self,'complaint_type'),self.complaint_type); f.addRow(ui_text(self,'complaint_sub_type'),self.sub_type); left.insertWidget(0,g)
        g2,f2=self._card(ui_text(self,'investigation_results'))
        self.investigation_summary=self._text(130); self.root_cause=self._text(90); self.capa_required=self._combo(['No','Yes','TBD']); self.capa_reason=self._text(70)
        f2.addRow(ui_text(self,'investigation_summary'),self.investigation_summary); f2.addRow(ui_text(self,'root_cause'),self.root_cause)
        f2.addRow(ui_text(self,'capa_required'),self.capa_required); f2.addRow(ui_text(self,'capa_reason'),self.capa_reason); right.insertWidget(0,g2)
        self.tabs.addTab(page,ui_text(self,'investigation'))

    def _build_closure_tab(self):
        page,left,right=self._two_column_page(); g,f=self._card(ui_text(self,'closure'))
        self.final_conclusion=self._text(110); self.close_as=self._combo(['--None--','Confirmed Complaint','Non Complaint','Duplicate','Cancelled'])
        self.completed_date=self._date(); self.final_reply=self._text(100)
        f.addRow(ui_text(self,'final_conclusion'),self.final_conclusion); f.addRow(ui_text(self,'close_as'),self.close_as)
        f.addRow(ui_text(self,'completed_date'),self.completed_date); f.addRow(ui_text(self,'final_reply_details'),self.final_reply); left.insertWidget(0,g)
        g2,f2=self._card(ui_text(self,'complainant_follow_up'))
        self.required_action=self._combo(['--None--','Notify Manager','Notify Authorities','Repair Product','Other'], True)
        self.action_description=self._text(90); self.responsible_person=self._line(); self.target_due_date=self._date()
        f2.addRow(ui_text(self,'required_action'),self.required_action); f2.addRow(ui_text(self,'action_description'),self.action_description)
        f2.addRow(ui_text(self,'responsible_person'),self.responsible_person); f2.addRow(ui_text(self,'target_final_reply_date'),self.target_due_date); right.insertWidget(0,g2)
        self.tabs.addTab(page,ui_text(self,'closure'))

    def _build_additional_tab(self):
        page,left,right=self._two_column_page(); g,f=self._card(ui_text(self,'complaint_information'))
        self.account=self._line(); self.contact=self._line(); self.occupation=self._line(); self.supplier=self._line()
        f.addRow(ui_text(self,'account'),self.account); f.addRow(ui_text(self,'contact'),self.contact)
        f.addRow(ui_text(self,'complainant_occupation'),self.occupation); f.addRow(ui_text(self,'supplier'),self.supplier); left.insertWidget(0,g)
        g2,f2=self._card(ui_text(self,'additional_information'))
        self.desc=self._text(170); self.desc.setPlaceholderText(ui_text(self,'english_only'))
        self.additional_info=self._text(100); self.output=self._combo(['Outlook','Template'], False)
        configured_output = str(self.settings.get('output_mode', 'Outlook')).title()
        self.output.setCurrentText(configured_output if configured_output in ('Outlook','Template') else 'Outlook')
        self.output.currentTextChanged.connect(self._sync_output_mode_from_additional)
        self.recipient_override=self._line('Automatically populated from Country; editable with semicolon-separated addresses')
        self.attachments=FeedbackAttachmentList(); self.attachments.setMinimumHeight(90)
        attach_bar=QHBoxLayout(); add_attach=QPushButton(ui_text(self,'add_photo_file')); remove_attach=QPushButton(ui_text(self,'remove_selected'))
        add_attach.clicked.connect(self.add_complaint_attachments); remove_attach.clicked.connect(self.remove_complaint_attachments)
        attach_bar.addWidget(add_attach); attach_bar.addWidget(remove_attach); attach_bar.addStretch()
        attach_box=QWidget(); attach_layout=QVBoxLayout(attach_box); attach_layout.setContentsMargins(0,0,0,0); attach_layout.addWidget(self.attachments); attach_layout.addLayout(attach_bar)
        f2.addRow(self._required('description',ui_text(self,'complaint_description'),self.desc,'additional'),self.desc)
        f2.addRow(ui_text(self,'additional_information'),self.additional_info); f2.addRow(ui_text(self,'outlook_to'),self.recipient_override)
        f2.addRow(ui_text(self,'photos_attachments'),attach_box); f2.addRow(ui_text(self,'output_mode'),self.output)
        if self.admin_mode:
            admin_lists=QPushButton(ui_text(self,'admin_edit_input_lists')); admin_lists.clicked.connect(self.edit_input_lists); f2.addRow('',admin_lists)
        right.insertWidget(0,g2)
        self.tabs.addTab(page,ui_text(self,'additional'))

    def add_complaint_attachments(self):
        files,_=QFileDialog.getOpenFileNames(self,ui_text(self,'select_complaint_files'),str(Path.home()),'Photos and files (*.jpg *.jpeg *.png *.bmp *.gif *.pdf *.txt *.log *.zip);;All Files (*.*)')
        for path in files:
            self.attachments.add_path(path)
        self.update_status()

    def remove_complaint_attachments(self):
        for item in self.attachments.selectedItems():
            self.attachments.takeItem(self.attachments.row(item))
        self.update_status()

    def _build_preview_tab(self):
        page=QWidget(); lay=QVBoxLayout(page); lay.setContentsMargins(14,14,14,14)
        bar=QHBoxLayout(); refresh=QPushButton(ui_text(self,'refresh_preview')); refresh.clicked.connect(self.refresh_preview)
        check=QPushButton(ui_text(self,'check_english')); check.clicked.connect(self.check_english)
        self.preview_output=QComboBox(); self.preview_output.addItems(['Outlook','Template'])
        self.preview_output.setCurrentText(self.output.currentText())
        self.preview_output.setMinimumWidth(145)
        self.preview_output.currentTextChanged.connect(self._sync_output_mode_from_preview)
        self.generate_button=QPushButton(); self.generate_button.clicked.connect(self.generate)
        export=QPushButton(ui_text(self,'salesforce_export')); export.clicked.connect(self.export_salesforce)
        bar.addWidget(refresh); bar.addWidget(check); bar.addStretch()
        bar.addWidget(QLabel(ui_text(self,'output_mode'))); bar.addWidget(self.preview_output)
        bar.addWidget(export); bar.addWidget(self.generate_button); lay.addLayout(bar)
        self.preview=QTextEdit(); self.preview.setReadOnly(True); self.preview.setStyleSheet('font-family:Consolas; background:#F8FBFF;'); lay.addWidget(self.preview)
        self._update_generate_button_text()
        self.tabs.addTab(page,ui_text(self,'preview'))

    def _sync_output_mode_from_additional(self, mode):
        preview_output = getattr(self, 'preview_output', None)
        if preview_output is not None and preview_output.currentText() != mode:
            preview_output.blockSignals(True); preview_output.setCurrentText(mode); preview_output.blockSignals(False)
        self._update_generate_button_text()

    def _sync_output_mode_from_preview(self, mode):
        if self.output.currentText() != mode:
            self.output.blockSignals(True); self.output.setCurrentText(mode); self.output.blockSignals(False)
        self._update_generate_button_text()

    def _update_generate_button_text(self):
        button = getattr(self, 'generate_button', None)
        if button is None:
            return
        if self.output.currentText() == 'Template':
            button.setText(ui_text(self,'open_template'))
            button.setToolTip('Open a copyable mail template without checking or starting Outlook.')
        else:
            button.setText(ui_text(self,'create_outlook_draft'))
            button.setToolTip('Create a draft in Classic Outlook. Template mode remains available as a fallback.')

    def _connect_validation(self):
        # Required fields are connected by the reusable ValidationManager.
        self.validation_manager.validate()

    def _widget_text(self,w):
        if w is None: return ''
        if isinstance(w,QLineEdit): return w.text().strip()
        if isinstance(w,QTextEdit): return w.toPlainText().strip()
        if isinstance(w,QComboBox):
            text=w.currentText().strip(); return '' if text in ('--None--','None') else text
        if isinstance(w,QDateEdit):
            return '' if w.date() == w.minimumDate() else w.date().toString('yyyy-MM-dd')
        return ''

    def english_text(self):
        names = (
            'subject', 'desc', 'symptom', 'investigation_summary', 'root_cause',
            'capa_reason', 'final_conclusion', 'final_reply',
            'action_description', 'additional_info'
        )
        return '\n'.join(self._widget_text(getattr(self, name, None)) for name in names)

    def update_status(self,*args):
        self.validation_manager.validate()

    def _apply_validation_result(self, result):
        missing = result['missing']
        self.progress.setValue(result['percent'])
        non_english = contains_non_english_text(self.english_text())
        warnings = len(missing) + (1 if non_english else 0)
        self.issue_count.setText(
            ui_text(self,'missing_required') + f': {len(missing)}' +
            ('  |  ' + ui_text(self,'non_english_detected') if non_english else '')
        )
        if warnings == 0:
            self.readiness.setText(ui_text(self,'ready'))
            self.readiness.setStyleSheet('padding:6px 12px; border-radius:10px; background:#D9F2DF; color:#17652A; font-weight:bold;')
        else:
            self.readiness.setText(ui_text(self,'warnings_count').format(count=warnings))
            self.readiness.setStyleSheet('padding:6px 12px; border-radius:10px; background:#FFF3CD; color:#7A5600; font-weight:bold;')
        self._update_validation_tabs(result)
        if hasattr(self, 'preview') and self.preview is not None and self.tabs.currentWidget() is self.preview.parentWidget():
            self.refresh_preview()

    def _update_validation_tabs(self, result):
        tab_by_section = {'basic': 0, 'medical': 1, 'additional': 4}
        title_key = {'basic': 'basic', 'medical': 'medical', 'additional': 'additional'}
        totals = result['section_totals']; complete = result['section_complete']
        for section, index in tab_by_section.items():
            if index >= self.tabs.count():
                continue
            total = totals.get(section, 0)
            done = complete.get(section, 0)
            ok = total > 0 and total == done
            prefix = '✓ ' if ok else '● '
            self.tabs.setTabText(index, prefix + ui_text(self, title_key[section]))
            self.tabs.tabBar().setTabTextColor(index, Qt.darkGreen if ok else Qt.red)
            missing_count = max(0, total-done)
            self.tabs.setTabToolTip(index, ui_text(self,'tab_complete') if ok else ui_text(self,'tab_missing').format(count=missing_count))

    def _section_tab_index(self, section):
        return {'basic':0, 'medical':1, 'additional':4}.get(section, 0)

    def jump_to_required_field(self, key):
        field = next((f for f in self.validation_manager.fields() if f['key']==key), None)
        if not field:
            return
        self.tabs.setCurrentIndex(self._section_tab_index(field['section']))
        widget = field['widget']
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                parent.ensureWidgetVisible(widget, 30, 30)
                break
            parent = parent.parentWidget()
        self.validation_manager.focus_field(key)

    def show_missing_fields_dialog(self, missing):
        dlg = QDialog(self)
        dlg.setWindowTitle(ui_text(self,'required_information'))
        dlg.resize(520, 430)
        lay = QVBoxLayout(dlg)
        intro = QLabel(ui_text(self,'missing_fields_instruction'))
        intro.setWordWrap(True); lay.addWidget(intro)
        items = QListWidget(); lay.addWidget(items, 1)
        for field in missing:
            item = QListWidgetItem(f"{ui_text(self, field['section'])} — {field['label']}")
            item.setData(Qt.UserRole, field['key'])
            items.addItem(item)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        jump = QPushButton(ui_text(self,'jump_to_field'))
        buttons.addButton(jump, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(dlg.reject)
        def do_jump(item=None):
            item = item or items.currentItem()
            if item is None: return
            key = item.data(Qt.UserRole)
            dlg.accept(); self.jump_to_required_field(key)
        jump.clicked.connect(do_jump)
        items.itemDoubleClicked.connect(do_jump)
        lay.addWidget(buttons)
        dlg.exec()

    def on_tab_changed(self,index):
        self._ensure_lazy_tab(index)
        previous=any(self.tabs.isTabEnabled(i) for i in range(0,index))
        following=any(self.tabs.isTabEnabled(i) for i in range(index+1,self.tabs.count()))
        self.prev_btn.setEnabled(previous); self.next_btn.setEnabled(following)
        if index==self.tabs.count()-1: self.refresh_preview()

    def populate_company_sites(self):
        """Populate Country from the company-scoped site list, then its hospitals/systems."""
        countries = sorted({h.get('country', '') for h in self.hospital_master if h.get('country')})
        previous = self.country.currentText()
        self._syncing_site_fields = True
        self.country.clear(); self.country.addItems(countries)
        if previous in countries:
            self.country.setCurrentText(previous)
        self._syncing_site_fields = False
        self.refresh_hospital(preserve=False)

    def on_country_changed(self, _text=''):
        if self._syncing_site_fields:
            return
        self.refresh_hospital(preserve=False)
        self.update_recipient_field()

    def update_recipient_field(self):
        if hasattr(self, 'recipient_override'):
            recipients=self.complaint_recipients(self.country.currentText())
            self.recipient_override.setText('; '.join(recipients))

    def on_hospital_changed(self, _text=''):
        if self._syncing_site_fields:
            return
        self.refresh_model(preserve=False)

    def on_model_changed(self, _text=''):
        if self._syncing_site_fields:
            return
        self.refresh_serial(preserve=False)

    def on_serial_changed(self, _text=''):
        if self._syncing_site_fields:
            return
        self.refresh_from_serial()

    def refresh_hospital(self, preserve=True):
        country = self.country.currentText()
        valid = [h.get('hospital_name','') for h in self.hospital_master
                 if h.get('country') == country and h.get('hospital_name')]
        valid = list(dict.fromkeys(valid))
        current = self.hospital.currentText() if preserve else ''
        self._syncing_site_fields = True
        self.hospital.clear(); self.hospital.addItems(valid)
        if current in valid:
            self.hospital.setCurrentText(current)
        self._syncing_site_fields = False
        self.refresh_model(preserve=False)

    def refresh_model(self, preserve=True):
        """Populate Model directly from the selected Hospital.

        Model used to be assigned only after Serial selection, so changing Hospital
        could leave a stale or blank Model.  Keep Hospital -> Model -> Serial as an
        explicit cascade and clear downstream values whenever the parent changes.
        """
        country = self.country.currentText(); hname = self.hospital.currentText()
        matches = [h for h in self.hospital_master
                   if h.get('country') == country and h.get('hospital_name') == hname]
        models = list(dict.fromkeys(str(m.get('type','')).strip() for m in matches
                                    if str(m.get('type','')).strip()))
        if '650' not in models:
            models.insert(0, '650')
        else:
            models = ['650'] + [m for m in models if m != '650']
        current = self.model.currentText() if preserve else '650'
        self._syncing_site_fields = True
        self.model.clear(); self.model.addItems(models)
        if current in models:
            self.model.setCurrentText(current)
        else:
            self.model.setCurrentText('650')
        self._syncing_site_fields = False
        self.refresh_serial(preserve=False)

    def _software_version_options(self, extra=None):
        base = self.field_options.get('software_version', [])
        values = [str(v) for v in base if str(v).strip()]
        for value in (extra or []):
            text = str(value).strip()
            if text and text not in values:
                values.append(text)
        return values

    def refresh_serial(self, preserve=True):
        country = self.country.currentText(); hname = self.hospital.currentText()
        selected_model = self.model.currentText().strip()
        matches = [h for h in self.hospital_master
                   if h.get('country') == country and h.get('hospital_name') == hname]
        if selected_model:
            model_matches = [h for h in matches if str(h.get('type','')).strip() == selected_model]
            if model_matches:
                matches = model_matches
        serials = list(dict.fromkeys(m.get('serial','') for m in matches if m.get('serial')))
        versions = []
        for m in matches:
            versions.extend(m.get('software_versions', []) or [])
        current = self.serial.currentText() if preserve else ''
        self._syncing_site_fields = True
        self.serial.clear(); self.serial.addItems(serials)
        if current in serials:
            self.serial.setCurrentText(current)
        current_sw = self.sw.currentText()
        self.sw.clear(); self.sw.addItems(self._software_version_options(versions))
        if current_sw and self.sw.findText(current_sw) >= 0:
            self.sw.setCurrentText(current_sw)
        elif self.sw.findText('7.33') >= 0:
            self.sw.setCurrentText('7.33')
        self._syncing_site_fields = False
        self.refresh_from_serial(); self.update_status()

    def refresh_from_serial(self):
        serial = self.serial.currentText()
        country=self.country.currentText(); hospital=self.hospital.currentText()
        matches = [h for h in self.hospital_master
                   if h.get('serial') == serial
                   and h.get('country') == country
                   and h.get('hospital_name') == hospital]
        if not matches:
            matches = [h for h in self.hospital_master if h.get('serial') == serial]
        if hasattr(self, 'mr_info'):
            self.mr_info.clear()
        if hasattr(self, 'distributor_fe'):
            self.distributor_fe.clear()
        self.account.clear()
        if matches:
            m = matches[0]
            # Serial may update dependent fields, but it must never push the user back
            # to a Country outside the current company-scoped selection.
            self._syncing_site_fields = True
            if m.get('country') in [self.country.itemText(i) for i in range(self.country.count())]:
                self.country.setCurrentText(m.get('country',''))
            if self.hospital.findText(m.get('hospital_name','')) >= 0:
                self.hospital.setCurrentText(m.get('hospital_name',''))
            self._syncing_site_fields = False
            self.product.setCurrentText(m.get('system') or m.get('system_number') or '')
            # Model is a complaint-entry default, not an installed-system lookup result.
            # Keep the display fixed at 650 even after Serial selection.
            self._syncing_site_fields = True
            if self.model.findText('650') < 0:
                self.model.insertItem(0, '650')
            self.model.setCurrentText('650')
            self._syncing_site_fields = False
            if m.get('software_versions'):
                current_sw = self.sw.currentText()
                self.sw.clear(); self.sw.addItems(self._software_version_options(m.get('software_versions', [])))
                if current_sw and self.sw.findText(current_sw) >= 0:
                    self.sw.setCurrentText(current_sw)
                elif self.sw.findText('7.33') >= 0:
                    self.sw.setCurrentText('7.33')
            if m.get('insightec_owner') and self.settings.get('company') == 'InSightec':
                self.owner.setText(m.get('insightec_owner'))
            fes=m.get('distributor_fes') or []
            if isinstance(fes,str):
                fes=[x.strip() for x in re.split(r'[;,|]+',fes) if x.strip()]
            linked_fes=list(dict.fromkeys([str(x).strip() for x in fes if str(x).strip()]))
            if not linked_fes and m.get('distributor'):
                linked_fes=[str(m.get('distributor')).strip()]
            self.distributor_fe.setText(', '.join(linked_fes))
            if m.get('mr_company') or m.get('mr_product'):
                mr_text = ' / '.join(v for v in [m.get('mr_company',''), m.get('magnetic_field',''), m.get('mr_product','')] if v)
                self.mr_info.setText(mr_text)
        self.update_status()

    def payload(self):
        value = self._widget_text
        return {
            'country': value(self.country), 'hospital_name': value(self.hospital), 'serial': value(self.serial),
            'software_version': value(self.sw), 'complaint_subject': value(self.subject),
            'complaint_description': value(self.desc), 'date_reported': value(self.date_reported),
            'complaint_number': value(self.complaint_number), 'event_date': value(self.event_date),
            'product': value(self.product), 'model': value(self.model), 'business_unit': value(self.business_unit),
            'owner': value(self.owner), 'distributor_fe': value(self.distributor_fe), 'usage_type': value(self.usage_type),
            'treatment_indication': value(self.treatment_indication), 'treatment_application': value(self.treatment_application),
            'affected_treatment': value(self.affected_treatment), 'next_scheduled_treatment': value(self.next_treatment),
            'adverse_event_occurred': value(self.adverse_occurred), 'adverse_event_type': value(self.adverse_type),
            'symptom': value(self.symptom), 'initial_awareness_date': value(self.initial_awareness),
            'supplemental_awareness_date': value(self.supplemental_awareness), 'received_mode': value(self.received_mode),
            'complaint_source': value(self.complaint_source), 'classification': value(self.classification),
            'criticality': value(self.criticality), 'complaint_type': value(self.complaint_type),
            'complaint_sub_type': value(self.sub_type), 'investigation_summary': value(self.investigation_summary),
            'root_cause': value(self.root_cause), 'capa_required': value(self.capa_required), 'capa_reason': value(self.capa_reason),
            'final_conclusion': value(self.final_conclusion), 'close_as': value(self.close_as),
            'completed_date': value(self.completed_date), 'final_reply_details': value(self.final_reply),
            'required_action': value(self.required_action), 'action_description': value(self.action_description),
            'responsible_person': value(self.responsible_person), 'target_due_date': value(self.target_due_date),
            'account': value(self.account), 'contact': value(self.contact), 'complainant_occupation': value(self.occupation),
            'supplier': value(self.supplier), 'additional_information': value(self.additional_info),
            'outlook_to': value(self.recipient_override), 'attachments': '; '.join(self.attachments.paths())
        }

    def missing_required(self): return [f['label'] for f in self.validation_manager.fields() if not self._widget_text(f['widget'])]
    def text_has_non_english(self): return contains_non_english_text(self.english_text())
    def check_english(self):
        if self.text_has_non_english(): QMessageBox.warning(self,ui_text(self,'english_check'),ui_text(self,'non_english_detected'))
        else: QMessageBox.information(self,ui_text(self,'english_check'),ui_text(self,'english_check_ok'))

    def refresh_preview(self):
        p=self.payload(); missing=self.missing_required(); lines=[ui_text(self,'salesforce_preview'),'='*72]
        recipient_text = '; '.join(self.complaint_recipients(p.get('country','')))
        lines += ['Complaint recipients: ' + (recipient_text or '(not configured)'), '']
        if missing: lines += [ui_text(self,'missing_required')+': '+', '.join(missing),'']
        for key,value in p.items():
            if value not in ('','--None--',None): lines.append(f'{key.replace("_"," ").title()}: {value}')
        self.preview.setPlainText('\n'.join(lines))

    def _validate_before_output(self):
        result = self.validation_manager.validate()
        if result['missing']:
            self.show_missing_fields_dialog(result['missing'])
            return False
        if self.text_has_non_english():
            QMessageBox.warning(self,ui_text(self,'english_check'),ui_text(self,'correct_non_english')); return False
        return True

    def complaint_recipients(self, country):
        item = {}
        if isinstance(self.recipient_master, dict):
            wanted=str(country).strip().casefold()
            for key,val in self.recipient_master.items():
                if str(key).strip().casefold() == wanted:
                    item=val; break
        values = item.get('to', []) if isinstance(item, dict) else []
        return [str(v).strip() for v in values if str(v).strip()]

    def complaint_mail_content(self):
        p = self.payload()
        template = read_json(APP_DIR/'templates/email_template.json', {})
        subject = template.get('subject', '[Complaint] {complaint_subject}').format(**p)
        body_lines=['Dear InSightec Team,','','Please find the complete complaint information below.','']
        for key,val in p.items():
            if key in ('outlook_to','attachments') or val in ('','--None--',None):
                continue
            body_lines.append(f'{key.replace("_"," ").title()}: {val}')
        paths=self.attachments.paths()
        if paths:
            body_lines += ['', 'Attachments:'] + [f'- {Path(x).name}' for x in paths]
        body_lines += ['', 'Best regards,']
        body='\n'.join(body_lines)
        manual=[x.strip() for x in re.split(r'[;,]', self.recipient_override.text()) if x.strip()]
        recipients = manual or self.complaint_recipients(p.get('country', ''))
        return recipients, subject, body

    def generate(self):
        if not self._validate_before_output():
            return
        recipients, subject, body = self.complaint_mail_content()
        if not recipients:
            QMessageBox.warning(self, ui_text(self,'outlook_recipient_missing'), ui_text(self,'outlook_recipient_missing_message'))
            return
        if not self.confirm_mail_preview(recipients, subject, body):
            return
        if self.attachments.paths():
            answer = QMessageBox.question(self, 'Attachments', f'{len(self.attachments.paths())} attachment(s) will be added. Continue?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if answer != QMessageBox.Yes: return
        if self.output.currentText() == 'Outlook':
            default_app = default_mail_app_name()
            if default_app and 'outlook' not in default_app.lower():
                QMessageBox.information(self, 'Default mail application', 'Outlook is not the default mail application. The app will still try Outlook directly. If it cannot connect, use Template mode and copy the fields into your company mail application.')
            result, detail = self.open_complaint_outlook_with_recovery(recipients, subject, body)
            if result == 'success':
                QMessageBox.information(self, ui_text(self,'complaint_tool'), ui_text(self,'feedback_opened_outlook'))
                log('Complaint Outlook draft opened: ' + subject)
                return
            if result == 'cancel':
                return
            log('Complaint Outlook fallback to template: ' + detail)
        self.show_complaint_template(recipients, subject, body)

    def confirm_mail_preview(self, recipients, subject, body):
        dlg = QDialog(self); dlg.setWindowTitle('Mail preview'); dlg.resize(840, 660)
        lay = QVBoxLayout(dlg)
        info = QLabel(f"To: {'; '.join(recipients)}\nSubject: {subject}\nAttachments: {len(self.attachments.paths())}"); info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body_box = QTextEdit(); body_box.setPlainText(body); body_box.setReadOnly(True)
        lay.addWidget(info); lay.addWidget(body_box,1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); buttons.button(QDialogButtonBox.Ok).setText('Create mail')
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject); lay.addWidget(buttons)
        return dlg.exec() == QDialog.Accepted

    def create_complaint_outlook_once(self, recipients, subject, body):
        try:
            import comtypes
            import comtypes.client
            # Initialize COM explicitly because this callback may run after
            # background work or from a packaged GUI process.
            initialized = False
            try:
                comtypes.CoInitialize()
                initialized = True
            except Exception:
                pass
            try:
                try:
                    outlook = comtypes.client.GetActiveObject('Outlook.Application')
                except Exception:
                    # CreateObject also starts Outlook when it is installed but
                    # has not yet registered an active COM object.
                    outlook = comtypes.client.CreateObject('Outlook.Application')
                mail = outlook.CreateItem(0)
                mail.To = '; '.join(recipients)
                mail.Subject = subject
                mail.Body = body
                for path in self.attachments.paths():
                    if Path(path).is_file():
                        mail.Attachments.Add(str(Path(path).resolve()))
                mail.Display(False)
                return True, ''
            finally:
                if initialized:
                    try:
                        comtypes.CoUninitialize()
                    except Exception:
                        pass
        except ModuleNotFoundError as exc:
            return False, f'Internal Outlook component is missing: {exc}'
        except Exception as exc:
            return False, f'{type(exc).__name__}: {exc}'

    def open_complaint_outlook_with_recovery(self, recipients, subject, body):
        last_detail = ''
        if not outlook_process_running():
            log('Outlook process is not running before complaint mail creation.')
        for attempt in range(1, 4):
            ok, detail = self.create_complaint_outlook_once(recipients, subject, body)
            if ok:
                return 'success', ''
            last_detail = detail
            log(f'Complaint Outlook attempt {attempt}/3 failed: {detail}')
            if 'Internal module error:' in detail or 'ModuleNotFoundError' in detail:
                answer = QMessageBox.question(
                    self, ui_text(self,'outlook_component_unavailable'),
                    ui_text(self,'outlook_component_message') + f'\n\n{detail}',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                return ('template', detail) if answer == QMessageBox.Yes else ('cancel', detail)

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle(ui_text(self,'outlook_not_ready'))
            box.setText(ui_text(self,'outlook_connect_failed') + f'\n\n{ui_text(self,"attempt")} {attempt}/3')
            box.setInformativeText(ui_text(self,'outlook_recovery_help'))
            box.addButton(ui_text(self,'retry'), QMessageBox.AcceptRole)
            open_button = box.addButton(ui_text(self,'open_outlook'), QMessageBox.ActionRole)
            template_button = box.addButton(ui_text(self,'open_template'), QMessageBox.DestructiveRole)
            cancel_button = box.addButton(QMessageBox.Cancel)
            box.exec()
            clicked = box.clickedButton()
            if clicked == template_button:
                self.output.setCurrentText('Template')
                return 'template', detail
            if clicked == cancel_button:
                return 'cancel', detail
            if clicked == open_button:
                started, start_detail = self.start_outlook_for_complaint()
                if not started:
                    QMessageBox.warning(self, ui_text(self,'outlook_start_failed'), start_detail)
                else:
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    try:
                        deadline = time.monotonic() + 15.0
                        while time.monotonic() < deadline:
                            QApplication.processEvents()
                            if outlook_process_running():
                                time.sleep(1.0); break
                            time.sleep(0.5)
                    finally:
                        QApplication.restoreOverrideCursor()

        answer = QMessageBox.question(
            self, ui_text(self,'outlook_connection_failed'),
            ui_text(self,'outlook_failed_three') + f'\n\n{last_detail}',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if answer == QMessageBox.Yes:
            self.output.setCurrentText('Template')
            return 'template', last_detail
        return 'cancel', last_detail

    def start_outlook_for_complaint(self):
        if not sys.platform.startswith('win'):
            return False, 'Automatic Outlook start is only supported on Windows.'
        errors=[]
        executable=find_classic_outlook_executable()
        if executable:
            try:
                subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                return True, ''
            except Exception as exc:
                errors.append(f'executable: {type(exc).__name__}: {exc}')
        try:
            os.startfile('outlook:')
            return True, ''
        except Exception as exc:
            errors.append(f'outlook URI: {type(exc).__name__}: {exc}')
        try:
            subprocess.Popen(['cmd','/c','start','','outlook:'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return True, ''
        except Exception as exc:
            errors.append(f'shell: {type(exc).__name__}: {exc}')
        return False, 'Classic Outlook could not be located or started. ' + ' | '.join(errors)

    def show_complaint_template(self, recipients, subject, body):
        dlg = QDialog(self); dlg.setWindowTitle(ui_text(self,'template_preview')); dlg.resize(860, 680)
        lay = QVBoxLayout(dlg)
        to_text = '; '.join(recipients)
        box = QTextEdit(); box.setPlainText('To: ' + to_text + '\nSubject: ' + subject + '\n\n' + body); lay.addWidget(box)
        row = QHBoxLayout()
        def copy_value(value, name):
            QApplication.clipboard().setText(value)
            QMessageBox.information(dlg, 'Copied', f'{name} copied to clipboard.')
        for label, value in [('Copy To',to_text),('Copy Subject',subject),('Copy Body',body),('Copy All',box.toPlainText())]:
            btn=QPushButton(label); btn.clicked.connect(lambda _=False,v=value,n=label: copy_value(v,n)); row.addWidget(btn)
        close = QPushButton(ui_text(self,'close')); close.clicked.connect(dlg.accept); row.addStretch(); row.addWidget(close); lay.addLayout(row)
        dlg.exec(); log('Generated complaint mail template: ' + subject)

    def export_salesforce(self):
        if not self._validate_before_output(): return
        out=APP_DIR/'exports'; out.mkdir(exist_ok=True); fn=out/f'salesforce_complaint_{datetime.datetime.now():%Y%m%d_%H%M%S}.json'; write_json(fn,self.payload()); QMessageBox.information(self,ui_text(self,'saved'),ui_text(self,'saved_path')+f'\n{fn}')

    def save_record(self):
        if not self._validate_before_output(): return False
        p=APP_DIR/'data'; p.mkdir(exist_ok=True); fn=p/f'complaint_{datetime.datetime.now():%Y%m%d_%H%M%S}.json'; write_json(fn,self.payload()); QMessageBox.information(self,ui_text(self,'saved'),ui_text(self,'saved_path')+f'\n{fn}'); return True

    def save_and_new(self):
        if self.save_record():
            self.accept()


class SalesforceWorkflowDialog(QDialog):
    """Email -> reviewed field mapping -> click-to-paste -> registration reply workflow."""
    SOURCE_ALIASES = {
        'complaint_subject': ('complaint subject', 'subject', 'issue subject'),
        'serial': ('serial number', 'system serial number', 'serial', 'sn'),
        'complaint_description': ('complaint description', 'description', 'issue description', 'details'),
        'country': ('country',),
        'hospital_name': ('hospital name', 'hospital', 'site', 'account'),
        'software_version': ('software version', 'sw version', 'sw'),
        'date_reported': ('date reported', 'reported date', 'awareness date'),
        'product': ('product', 'model'),
        'reporter': ('reporter', 'reported by', 'contact'),
    }

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings = main_window.settings
        self.profile = read_json(APP_DIR/'profiles/salesforce_profile_default.json', {})
        self.mail_sender = ''
        self.mail_subject = ''
        self.mail_body = ''
        self.source_id = ''
        self._paste_armed = False
        self._paste_seen_down = False
        self._paste_value = ''
        self._paste_label = ''
        self.setWindowTitle('Salesforce Complaint Workflow')
        self.resize(1080, 780)
        self._build_ui()
        self._paste_timer = QTimer(self)
        self._paste_timer.setInterval(35)
        self._paste_timer.timeout.connect(self._poll_next_browser_click)

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel('Salesforce Complaint Workflow')
        title.setFont(QFont('Arial', 20, QFont.Bold))
        root.addWidget(title)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)

        # 1: source email
        source = QWidget(); sl = QVBoxLayout(source)
        hint = QLabel('Load the received complaint email, then review the extracted values before Salesforce input.')
        hint.setWordWrap(True); sl.addWidget(hint)
        buttons = QHBoxLayout()
        for text, fn in (
            ('Read selected Outlook email', self.read_selected_outlook_mail),
            ('Open .eml / text file', self.open_mail_file),
            ('Paste email text', self.paste_mail_text),
        ):
            b=QPushButton(text); b.clicked.connect(fn); buttons.addWidget(b)
        buttons.addStretch(); sl.addLayout(buttons)
        self.mail_meta = QLabel('No email loaded.'); self.mail_meta.setTextInteractionFlags(Qt.TextSelectableByMouse); sl.addWidget(self.mail_meta)
        self.mail_text = QTextEdit(); self.mail_text.setPlaceholderText('Loaded or pasted email body appears here.'); sl.addWidget(self.mail_text,1)
        parse_btn=QPushButton('Extract and review fields'); parse_btn.clicked.connect(self.extract_fields); sl.addWidget(parse_btn)
        self.tabs.addTab(source, '1. Email')

        # 2: review
        review = QWidget(); rl=QVBoxLayout(review)
        self.review_table=QTableWidget(0,4); self.review_table.setHorizontalHeaderLabels(['Source key','Salesforce field','Value','Status'])
        self.review_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.review_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.review_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
        self.review_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents)
        rl.addWidget(self.review_table,1)
        row=QHBoxLayout(); back=QPushButton('Back to email'); back.clicked.connect(lambda:self.tabs.setCurrentIndex(0))
        proceed=QPushButton('Confirm values and continue'); proceed.clicked.connect(self.prepare_input_page)
        row.addWidget(back); row.addStretch(); row.addWidget(proceed); rl.addLayout(row)
        self.tabs.addTab(review,'2. Review')

        # 3: guided input
        input_page=QWidget(); il=QVBoxLayout(input_page)
        info=QLabel('Select a row and press “Arm next browser click”. Then click the matching Salesforce field in Edge. The value will be pasted into that field. The application never presses Save.')
        info.setWordWrap(True); il.addWidget(info)
        bar=QHBoxLayout()
        open_sf=QPushButton('Open Salesforce'); open_sf.clicked.connect(self.open_salesforce)
        arm=QPushButton('Arm next browser click'); arm.clicked.connect(self.arm_selected_field)
        copy=QPushButton('Copy selected value'); copy.clicked.connect(self.copy_selected_value)
        stop=QPushButton('Cancel armed paste'); stop.clicked.connect(self.cancel_armed_paste)
        for b in (open_sf,arm,copy,stop): bar.addWidget(b)
        bar.addStretch(); il.addLayout(bar)
        self.input_status=QLabel('Ready.'); self.input_status.setStyleSheet('padding:8px; background:#EEF5FB;'); il.addWidget(self.input_status)
        self.input_table=QTableWidget(0,4); self.input_table.setHorizontalHeaderLabels(['Salesforce field','Value','Input status','Source key'])
        self.input_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.input_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.input_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
        self.input_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents)
        self.input_table.doubleClicked.connect(self.arm_selected_field)
        il.addWidget(self.input_table,1)
        done=QPushButton('Salesforce complaint registered — continue'); done.clicked.connect(self.open_completion_page); il.addWidget(done)
        self.tabs.addTab(input_page,'3. Salesforce Input')

        # 4: number + reply
        complete=QWidget(); cl=QVBoxLayout(complete)
        form=QFormLayout(); self.complaint_number=QLineEdit(); self.complaint_number.setPlaceholderText('Enter the number generated by Salesforce')
        self.complaint_number.textChanged.connect(self.refresh_reply_preview)
        form.addRow('Complaint Number',self.complaint_number); cl.addLayout(form)
        self.reply_preview=QTextEdit(); cl.addWidget(self.reply_preview,1)
        mode_row=QHBoxLayout(); mode_row.addWidget(QLabel('Mail output'))
        self.reply_mode=QComboBox(); self.reply_mode.addItems(['Outlook','Template']); self.reply_mode.setCurrentText(str(self.settings.get('output_mode','Outlook')).title())
        mode_row.addWidget(self.reply_mode); mode_row.addStretch(); cl.addLayout(mode_row)
        actions=QHBoxLayout()
        create=QPushButton('Create registration reply'); create.clicked.connect(self.create_registration_reply)
        save=QPushButton('Save workflow record'); save.clicked.connect(self.save_workflow_record)
        finish=QPushButton('Complete'); finish.clicked.connect(self.accept)
        actions.addWidget(create); actions.addWidget(save); actions.addStretch(); actions.addWidget(finish); cl.addLayout(actions)
        self.tabs.addTab(complete,'4. Registration Reply')

        self.tabs.setTabEnabled(1,False); self.tabs.setTabEnabled(2,False); self.tabs.setTabEnabled(3,False)

    def _profile_fields(self):
        fields=list(self.profile.get('fields',[]))
        existing={f.get('source') for f in fields}
        defaults=[
            ('country','Country','text'),('hospital_name','Hospital Name','text'),
            ('software_version','Software Version','text'),('date_reported','Date Reported','text')
        ]
        for source,label,kind in defaults:
            if source not in existing: fields.append({'source':source,'salesforce_label':label,'type':kind})
        return fields

    def read_selected_outlook_mail(self):
        try:
            import comtypes, comtypes.client
            initialized=False
            try: comtypes.CoInitialize(); initialized=True
            except Exception: pass
            try:
                outlook=comtypes.client.GetActiveObject('Outlook.Application')
                explorer=outlook.ActiveExplorer()
                selection=explorer.Selection if explorer else None
                if not selection or selection.Count < 1:
                    raise RuntimeError('Select one received email in Classic Outlook first.')
                item=selection.Item(1)
                self.mail_subject=str(getattr(item,'Subject','') or '')
                self.mail_body=str(getattr(item,'Body','') or '')
                try: self.mail_sender=str(item.SenderEmailAddress or '')
                except Exception: self.mail_sender=''
                self.source_id=str(getattr(item,'EntryID','') or '')
            finally:
                if initialized:
                    try: comtypes.CoUninitialize()
                    except Exception: pass
            self._show_loaded_mail()
        except Exception as exc:
            QMessageBox.warning(self,'Outlook email could not be read',f'{type(exc).__name__}: {exc}\n\nUse .eml/text import or paste mode as a fallback.')

    def open_mail_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Open complaint email',str(Path.home()),'Email and text (*.eml *.txt);;All Files (*.*)')
        if not path: return
        try:
            if path.lower().endswith('.eml'):
                from email import policy
                from email.parser import BytesParser
                msg=BytesParser(policy=policy.default).parse(open(path,'rb'))
                self.mail_subject=str(msg.get('subject',''))
                self.mail_sender=str(msg.get('from',''))
                if msg.is_multipart():
                    part=msg.get_body(preferencelist=('plain','html'))
                    self.mail_body=part.get_content() if part else ''
                else: self.mail_body=msg.get_content()
            else:
                self.mail_body=Path(path).read_text(encoding='utf-8',errors='replace')
                self.mail_subject=''; self.mail_sender=''
            self.source_id=str(Path(path).resolve()); self._show_loaded_mail()
        except Exception as exc: QMessageBox.critical(self,'Open email failed',f'{type(exc).__name__}: {exc}')

    def paste_mail_text(self):
        text=QApplication.clipboard().text()
        if not text:
            text,ok=QInputDialog.getMultiLineText(self,'Paste complaint email','Email content:')
            if not ok: return
        self.mail_body=text; self.source_id='clipboard'; self._show_loaded_mail()

    def _show_loaded_mail(self):
        self.mail_text.setPlainText(self.mail_body)
        self.mail_meta.setText(f'From: {self.mail_sender or "Unknown"}\nSubject: {self.mail_subject or "Unknown"}')

    def _extract_label_value(self, text, aliases):
        for alias in aliases:
            pattern=rf'(?im)^\s*{re.escape(alias)}\s*[:：]\s*(.+?)\s*$'
            match=re.search(pattern,text)
            if match: return match.group(1).strip()
        return ''

    def extract_fields(self):
        self.mail_body=self.mail_text.toPlainText().strip()
        if not self.mail_body:
            QMessageBox.warning(self,'Email required','Load or paste the received email first.'); return
        combined=(f'Subject: {self.mail_subject}\n'+self.mail_body).strip()
        self.review_table.setRowCount(0)
        for field in self._profile_fields():
            source=str(field.get('source','')); label=str(field.get('salesforce_label',source))
            aliases=self.SOURCE_ALIASES.get(source,(label,source.replace('_',' ')))
            value=self._extract_label_value(combined,aliases)
            if source=='complaint_subject' and not value: value=self.mail_subject
            if source=='complaint_description' and not value: value=self.mail_body
            row=self.review_table.rowCount(); self.review_table.insertRow(row)
            self.review_table.setItem(row,0,QTableWidgetItem(source)); self.review_table.item(row,0).setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            self.review_table.setItem(row,1,QTableWidgetItem(label)); self.review_table.item(row,1).setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            self.review_table.setItem(row,2,QTableWidgetItem(value))
            self.review_table.setItem(row,3,QTableWidgetItem('Found' if value else 'Review required'))
            self.review_table.item(row,3).setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        self.tabs.setTabEnabled(1,True); self.tabs.setCurrentIndex(1)

    def prepare_input_page(self):
        self.input_table.setRowCount(0)
        for r in range(self.review_table.rowCount()):
            source=self.review_table.item(r,0).text(); label=self.review_table.item(r,1).text(); value=self.review_table.item(r,2).text().strip()
            row=self.input_table.rowCount(); self.input_table.insertRow(row)
            for c,text in enumerate((label,value,'Pending' if value else 'Empty',source)):
                self.input_table.setItem(row,c,QTableWidgetItem(text))
                self.input_table.item(row,c).setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        self.tabs.setTabEnabled(2,True); self.tabs.setCurrentIndex(2)

    def open_salesforce(self):
        import webbrowser
        url=str(self.settings.get('salesforce_complaint_url') or self.profile.get('target_url') or '').strip()
        if not url:
            url,ok=QInputDialog.getText(self,'Salesforce URL','Enter the Salesforce new complaint URL:')
            if not ok or not url.strip(): return
            url=url.strip(); self.settings['salesforce_complaint_url']=url; write_json(APP_DIR/'config/settings.json',self.settings)
        webbrowser.open(url)

    def _selected_input(self):
        row=self.input_table.currentRow()
        if row<0: return None
        return row,self.input_table.item(row,0).text(),self.input_table.item(row,1).text()

    def copy_selected_value(self):
        selected=self._selected_input()
        if not selected: QMessageBox.information(self,'Select a field','Select a Salesforce field row first.'); return
        row,label,value=selected; QApplication.clipboard().setText(value); self.input_status.setText(f'Copied: {label}')

    def arm_selected_field(self, *_):
        selected=self._selected_input()
        if not selected: QMessageBox.information(self,'Select a field','Select a Salesforce field row first.'); return
        row,label,value=selected
        if not value: QMessageBox.warning(self,'Empty value',f'{label} has no value. Return to Review and enter it first.'); return
        if not sys.platform.startswith('win'):
            QApplication.clipboard().setText(value); QMessageBox.information(self,'Copied',f'{label} copied. Paste it into Salesforce manually.'); return
        QApplication.clipboard().setText(value)
        self._paste_row=row; self._paste_label=label; self._paste_value=value; self._paste_armed=True; self._paste_seen_down=False
        self.input_status.setText(f'Armed: click the “{label}” field in Edge. The value will be pasted automatically.')
        self._paste_timer.start()

    def cancel_armed_paste(self):
        self._paste_armed=False; self._paste_timer.stop(); self.input_status.setText('Armed paste cancelled.')

    def _foreground_process_name(self):
        try:
            import ctypes
            from ctypes import wintypes
            hwnd=ctypes.windll.user32.GetForegroundWindow(); pid=wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            PROCESS_QUERY_LIMITED_INFORMATION=0x1000
            handle=ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,False,pid.value)
            if not handle: return ''
            try:
                size=wintypes.DWORD(1024); buf=ctypes.create_unicode_buffer(1024)
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size)):
                    return Path(buf.value).name.lower()
            finally: ctypes.windll.kernel32.CloseHandle(handle)
        except Exception: pass
        return ''

    def _poll_next_browser_click(self):
        if not self._paste_armed: self._paste_timer.stop(); return
        try:
            import ctypes
            down=bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
            if down and not self._paste_seen_down:
                process=self._foreground_process_name()
                if process not in ('msedge.exe','chrome.exe'):
                    self.input_status.setText('Waiting: the next click must be inside Microsoft Edge or Chrome.')
                    return
                self._paste_seen_down=True
            elif self._paste_seen_down and not down:
                self._paste_armed=False; self._paste_timer.stop()
                QTimer.singleShot(180,self._send_ctrl_v)
        except Exception as exc:
            self.cancel_armed_paste(); QMessageBox.warning(self,'Automatic paste failed',str(exc))

    def _send_ctrl_v(self):
        try:
            import ctypes
            KEYEVENTF_KEYUP=0x0002; VK_CONTROL=0x11; VK_V=0x56
            ctypes.windll.user32.keybd_event(VK_CONTROL,0,0,0); ctypes.windll.user32.keybd_event(VK_V,0,0,0)
            ctypes.windll.user32.keybd_event(VK_V,0,KEYEVENTF_KEYUP,0); ctypes.windll.user32.keybd_event(VK_CONTROL,0,KEYEVENTF_KEYUP,0)
            self.input_table.item(self._paste_row,2).setText('Pasted')
            self.input_status.setText(f'Pasted: {self._paste_label}. Review the Salesforce field before continuing.')
            log(f'Salesforce field pasted: {self._paste_label}')
        except Exception as exc: QMessageBox.warning(self,'Paste failed',f'{type(exc).__name__}: {exc}')

    def open_completion_page(self):
        self.tabs.setTabEnabled(3,True); self.tabs.setCurrentIndex(3); self.refresh_reply_preview()

    def _review_values(self):
        values={}
        for r in range(self.review_table.rowCount()): values[self.review_table.item(r,0).text()]=self.review_table.item(r,2).text().strip()
        return values

    def _reply_parts(self):
        values=self._review_values(); number=self.complaint_number.text().strip()
        subject=f'RE: {self.mail_subject or values.get("complaint_subject", "Complaint report")} – Complaint No. {number or "[Complaint Number]"}'
        body=(f'Dear Customer,\n\nThank you for reporting this issue.\n\n'
              f'The complaint has been registered in Salesforce with the following complaint number:\n\n'
              f'Complaint No.: {number or "[Complaint Number]"}\n\n'
              f'Site: {values.get("hospital_name","")}\nSystem Serial Number: {values.get("serial","")}\n'
              f'Subject: {values.get("complaint_subject",self.mail_subject)}\n\n'
              'Please use the complaint number above for any further communication regarding this case.\n\n'
              f'Best regards,\n{self.settings.get("user","")}')
        return self.mail_sender,subject,body

    def refresh_reply_preview(self):
        to,subject,body=self._reply_parts(); self.reply_preview.setPlainText(f'To: {to}\nSubject: {subject}\n\n{body}')

    def create_registration_reply(self):
        number=self.complaint_number.text().strip()
        if not number: QMessageBox.warning(self,'Complaint Number required','Enter the Complaint Number generated by Salesforce.'); return
        to,subject,body=self._reply_parts()
        if self.reply_mode.currentText()=='Outlook':
            ok,detail=self._create_outlook_reply(to,subject,body)
            if ok:
                QMessageBox.information(self,'Reply prepared','The registration reply draft was opened in Classic Outlook.'); self.save_workflow_record(silent=True); return
            QMessageBox.warning(self,'Outlook unavailable',detail+'\n\nTemplate mode will be opened instead.')
            self.reply_mode.setCurrentText('Template')
        self._show_reply_template(to,subject,body); self.save_workflow_record(silent=True)

    def _create_outlook_reply(self,to,subject,body):
        try:
            import comtypes,comtypes.client
            initialized=False
            try: comtypes.CoInitialize(); initialized=True
            except Exception: pass
            try:
                try: outlook=comtypes.client.GetActiveObject('Outlook.Application')
                except Exception: outlook=comtypes.client.CreateObject('Outlook.Application')
                mail=outlook.CreateItem(0); mail.To=to; mail.Subject=subject; mail.Body=body; mail.Display(False)
                return True,''
            finally:
                if initialized:
                    try: comtypes.CoUninitialize()
                    except Exception: pass
        except Exception as exc: return False,f'{type(exc).__name__}: {exc}'

    def _show_reply_template(self,to,subject,body):
        dlg=QDialog(self); dlg.setWindowTitle('Registration Reply Template'); dlg.resize(820,620); lay=QVBoxLayout(dlg)
        text=QTextEdit(); text.setPlainText(f'To: {to}\nSubject: {subject}\n\n{body}'); lay.addWidget(text,1)
        row=QHBoxLayout()
        for label,value in [('Copy To',to),('Copy Subject',subject),('Copy Body',body),('Copy All',text.toPlainText())]:
            b=QPushButton(label); b.clicked.connect(lambda _=False,v=value: QApplication.clipboard().setText(v)); row.addWidget(b)
        close=QPushButton('Close'); close.clicked.connect(dlg.accept); row.addStretch(); row.addWidget(close); lay.addLayout(row); dlg.exec()

    def save_workflow_record(self, silent=False):
        number=self.complaint_number.text().strip(); values=self._review_values()
        record={'saved_at':datetime.datetime.now().isoformat(timespec='seconds'),'source_id':self.source_id,'original_sender':self.mail_sender,
                'original_subject':self.mail_subject,'complaint_number':number,'fields':values,'mail_mode':self.reply_mode.currentText(),
                'user':self.settings.get('user',''),'input_status':{self.input_table.item(r,0).text():self.input_table.item(r,2).text() for r in range(self.input_table.rowCount())}}
        out=APP_DIR/'data'/'salesforce_workflows'; out.mkdir(parents=True,exist_ok=True)
        path=out/f'salesforce_workflow_{datetime.datetime.now():%Y%m%d_%H%M%S}.json'; write_json(path,record)
        log(f'Salesforce workflow saved: {path.name}')
        if not silent: QMessageBox.information(self,'Workflow saved',f'Saved to:\n{path}')



class FeedbackAttachmentList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setMinimumHeight(105)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path:
                    self.add_path(path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def add_path(self, path):
        path = str(Path(path))
        existing = {self.item(i).data(Qt.UserRole) for i in range(self.count())}
        if path not in existing and Path(path).is_file():
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.addItem(item)

    def paths(self):
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]


class FeedbackDialog(QDialog):
    def __init__(self, parent=None, complaint_context=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = getattr(parent, 'settings', read_json(APP_DIR/'config/settings.json', {}))
        self.version = getattr(parent, 'version', read_json(APP_DIR/'app_version.json', {}))
        self.complaint_context = complaint_context or self.load_latest_complaint()
        self.feedback_dir = APP_DIR/'feedback'
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.engine = FeedbackEngine(APP_DIR, self.settings.get('feedback_to','masakii@insightec.com'), APP_DIR/'logs', self.feedback_dir)
        self.setWindowTitle(ui_text(self,'feedback_title'))
        self.resize(900, 790)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)

        intro = QLabel(ui_text(self,'feedback_intro'))
        intro.setWordWrap(True)
        intro.setStyleSheet(f'color:{PRIMARY}; font-weight:bold;')
        layout.addWidget(intro)

        form = QFormLayout()
        self.category = QComboBox(); [self.category.addItem(ui_text(self,k),v) for k,v in [('bug_report','Bug Report'),('improvement_request','Improvement Request'),('new_feature','New Feature'),('question','Question'),('validation_result','Validation Result')]]
        self.priority = QComboBox(); [self.priority.addItem(ui_text(self,k),v) for k,v in [('low','Low'),('normal','Normal'),('high','High'),('critical','Critical')]]
        self.reproducible = QComboBox(); [self.reproducible.addItem(ui_text(self,k),v) for k,v in [('unknown','Unknown'),('yes','Yes'),('no','No'),('sometimes','Sometimes')]]
        self.related_tool = QComboBox(); self.related_tool.addItems(['Complaint Service Hub','Complaint Input','Salesforce','Update ZIP','Settings','System No. Request'])
        self.mode = QComboBox(); self.mode.addItems(['Outlook','Template']); self.mode.setCurrentText(self.settings.get('feedback_mode', self.settings.get('output_mode','Outlook')).title())
        form.addRow(ui_text(self,'category'), self.category)
        form.addRow(ui_text(self,'priority'), self.priority)
        form.addRow(ui_text(self,'reproducible'), self.reproducible)
        form.addRow(ui_text(self,'related_tool'), self.related_tool)
        form.addRow(ui_text(self,'send_mode'), self.mode)
        layout.addLayout(form)

        self.context_group = QGroupBox(ui_text(self,'complaint_context_auto'))
        context_form = QFormLayout(self.context_group)
        self.context_preview = QTextEdit(); self.context_preview.setReadOnly(True); self.context_preview.setMaximumHeight(130)
        self.context_preview.setPlainText(self.context_text())
        context_form.addRow(self.context_preview)
        layout.addWidget(self.context_group)

        layout.addWidget(QLabel(ui_text(self,'comment_issue_detail')))
        self.comment = QTextEdit(); self.comment.setMinimumHeight(180)
        self.comment.setPlainText(ui_text(self,'feedback_comment_template'))
        layout.addWidget(self.comment)

        attach_row = QHBoxLayout()
        for text, fn in [(ui_text(self,'capture_screenshot'), self.capture_screenshot),(ui_text(self,'add_files'), self.add_files),(ui_text(self,'attach_recent_logs'), self.add_recent_logs),(ui_text(self,'create_validation_report'), self.create_validation_report),(ui_text(self,'remove_selected'), self.remove_selected)]:
            b=QPushButton(text); b.clicked.connect(fn); attach_row.addWidget(b)
        attach_row.addStretch()
        layout.addLayout(attach_row)
        self.attachments = FeedbackAttachmentList()
        self.attachments.setToolTip(ui_text(self,'attachment_drop_tip'))
        layout.addWidget(self.attachments)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        create = QPushButton(ui_text(self,'create_feedback'))
        create.setStyleSheet(f'background:{PRIMARY}; color:white; padding:8px 18px; font-weight:bold;')
        create.clicked.connect(self.submit)
        buttons.addButton(create, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_latest_complaint(self):
        files = sorted((APP_DIR/'data').glob('complaint_*.json'), key=lambda x: x.stat().st_mtime, reverse=True) if (APP_DIR/'data').exists() else []
        return read_json(files[0], {}) if files else {}

    def context_text(self):
        c=self.complaint_context or {}
        if not c:
            return ui_text(self,'no_complaint_context')
        labels=[(ui_text(self,'country'),'country'),(ui_text(self,'hospital_name'),'hospital_name'),(ui_text(self,'serial_number'),'serial'),(ui_text(self,'software_version'),'software_version'),(ui_text(self,'complaint_subject'),'complaint_subject'),(ui_text(self,'complaint'),'complaint_description')]
        return '\n'.join(f'{label}: {c.get(key, "")}' for label,key in labels)

    def add_files(self):
        files,_=QFileDialog.getOpenFileNames(self,ui_text(self,'select_attachment_files'),str(APP_DIR),'All Files (*.*)')
        for f in files: self.attachments.add_path(f)

    def capture_screenshot(self):
        try:
            screen=QApplication.primaryScreen()
            if screen is None: raise RuntimeError('No screen was detected.')
            stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            path=self.feedback_dir/f'screenshot_{stamp}.png'
            pix=screen.grabWindow(0)
            if not pix.save(str(path), 'PNG'): raise RuntimeError('Screenshot could not be saved.')
            self.attachments.add_path(path)
            QMessageBox.information(self,ui_text(self,'screenshot'),ui_text(self,'screenshot_saved')+f'\n{path.name}')
        except Exception as exc:
            QMessageBox.warning(self,ui_text(self,'screenshot_unavailable'),str(exc))

    def add_recent_logs(self):
        logs=sorted((APP_DIR/'logs').glob('*.log'), key=lambda p:p.stat().st_mtime, reverse=True)[:5]
        for item in logs: self.attachments.add_path(item)
        if not logs: QMessageBox.information(self,ui_text(self,'logs'),ui_text(self,'no_logs_found'))

    def feedback_context(self):
        return build_runtime_context(
            application='InSightec Complaint Service Hub',
            application_version=self.version.get('program',''),
            build=self.version.get('build',''),
            company=self.settings.get('company',''),
            user=self.settings.get('actual_user') or self.settings.get('user',''),
            language=self.settings.get('language',''),
            current_page='Complaint Input' if self.complaint_context else 'Feedback',
            related_tool=self.related_tool.currentText(),
            extra=self.complaint_context or {},
        )

    def create_validation_report(self):
        path = self.engine.create_validation_report(self.feedback_context())
        self.attachments.add_path(path)

    def remove_selected(self):
        for item in self.attachments.selectedItems():
            self.attachments.takeItem(self.attachments.row(item))

    def feedback_request(self):
        return FeedbackRequest(
            category=self.category.currentData() or self.category.currentText(),
            priority=self.priority.currentData() or self.priority.currentText(),
            reproducible=self.reproducible.currentData() or self.reproducible.currentText(),
            comment=self.comment.toPlainText(),
            mode=self.mode.currentText().lower(),
            attachments=self.attachments.paths(),
            context=self.feedback_context(),
        )

    def make_body(self):
        return self.engine.build_body(self.feedback_request())

    def submit(self):
        if contains_non_english_text(self.comment.toPlainText()):
            QMessageBox.warning(self, ui_text(self,'english_check'), ui_text(self,'feedback_body_must_be_english'))
            return
        request = self.feedback_request()
        body, outputs = self.engine.prepare(request)
        if contains_non_english_text(body):
            QMessageBox.warning(self, ui_text(self,'english_check'), ui_text(self,'generated_body_not_english'))
            return
        template = outputs['template']
        manifest = outputs['manifest']
        files = request.attachments
        self.settings['feedback_mode']=self.mode.currentText()
        write_json(APP_DIR/'config/settings.json', self.settings)
        if self.mode.currentText()=='Outlook':
            result, detail = self.open_outlook_with_recovery(body, files)
            if result == 'success':
                log(f'Feedback Outlook draft opened: {manifest.name}')
                QMessageBox.information(self,ui_text(self,'feedback'),ui_text(self,'feedback_opened_outlook'))
                self.accept(); return
            if result == 'cancel':
                return
            log(f'Feedback Outlook fallback to template: {detail}')
        self.show_template(body, template)

    def create_outlook_draft_once(self, body, files):
        try:
            import comtypes
            import comtypes.stream
            import comtypes.client
            try:
                outlook = comtypes.client.GetActiveObject('Outlook.Application')
            except Exception:
                return False, 'Outlook is not running or COM is not ready.'
            mail=outlook.CreateItem(0)
            mail.To=self.settings.get('feedback_to','masakii@insightec.com')
            mail.Subject=self.engine.build_subject(self.feedback_request())
            mail.Body=body
            attached=set()
            for item in files:
                path=Path(item)
                if path.is_file():
                    resolved=str(path.resolve()); key=resolved.lower()
                    if key not in attached:
                        mail.Attachments.Add(resolved); attached.add(key)
            for item in sorted((APP_DIR/'logs').glob('*.log'), key=lambda p:p.stat().st_mtime, reverse=True)[:3]:
                resolved=str(item.resolve()); key=resolved.lower()
                if key not in attached:
                    mail.Attachments.Add(resolved); attached.add(key)
            mail.Display(False)
            return True,''
        except ModuleNotFoundError as exc:
            return False, f'Internal module error: {exc}'
        except Exception as exc:
            return False,f'{type(exc).__name__}: {exc}'

    def start_outlook(self):
        try:
            if sys.platform.startswith('win'):
                try:
                    os.startfile('outlook.exe')
                except Exception:
                    subprocess.Popen(['outlook.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, ''
            return False, 'Automatic Outlook start is only supported on Windows.'
        except Exception as exc:
            return False, f'{type(exc).__name__}: {exc}'

    def open_outlook_with_recovery(self, body, files):
        last_detail = ''
        if not outlook_process_running():
            log('Outlook process is not running before complaint mail creation.')
        for attempt in range(1, 4):
            ok, detail = self.create_outlook_draft_once(body, files)
            if ok:
                return 'success', ''
            last_detail = detail
            log(f'Outlook feedback attempt {attempt}/3 failed: {detail}')

            # Packaging or internal module failures cannot be fixed by retrying.
            if 'Internal module error:' in detail or 'ModuleNotFoundError' in detail:
                answer = QMessageBox.question(
                    self,
                    ui_text(self,'outlook_component_unavailable'),
                    ui_text(self,'outlook_component_message') + f'\n\n{detail}',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                return ('template', detail) if answer == QMessageBox.Yes else ('cancel', detail)

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle(ui_text(self,'outlook_not_ready'))
            box.setText(ui_text(self,'outlook_connect_failed') + f'\n\n{ui_text(self,"attempt")} {attempt}/3')
            box.setInformativeText(
                ui_text(self,'outlook_recovery_help')
            )
            retry_button = box.addButton(ui_text(self,'retry'), QMessageBox.AcceptRole)
            open_button = box.addButton(ui_text(self,'open_outlook'), QMessageBox.ActionRole)
            template_button = box.addButton(ui_text(self,'open_template'), QMessageBox.DestructiveRole)
            cancel_button = box.addButton(QMessageBox.Cancel)
            box.exec()
            clicked = box.clickedButton()

            if clicked == template_button:
                return 'template', detail
            if clicked == cancel_button:
                return 'cancel', detail
            if clicked == open_button:
                started, start_detail = self.start_outlook()
                if not started:
                    QMessageBox.warning(self, ui_text(self,'outlook_start_failed'), start_detail)
                else:
                    # Give Outlook time to register its COM server before the next attempt.
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    try:
                        deadline = time.monotonic() + 15.0
                        while time.monotonic() < deadline:
                            QApplication.processEvents()
                            if outlook_process_running():
                                time.sleep(1.0); break
                            time.sleep(0.5)
                    finally:
                        QApplication.restoreOverrideCursor()
            # Retry button proceeds immediately to the next loop iteration.

        answer = QMessageBox.question(
            self,
            ui_text(self,'outlook_connection_failed'),
            ui_text(self,'outlook_failed_three') + f'\n\n{last_detail}',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        return ('template', last_detail) if answer == QMessageBox.Yes else ('cancel', last_detail)

    def show_template(self, body, path):
        dlg=QDialog(self); dlg.setWindowTitle(ui_text(self,'feedback_mail_template')); dlg.resize(820,650)
        lay=QVBoxLayout(dlg); info=QLabel(ui_text(self,'template_saved') + f': {path}'); info.setWordWrap(True); lay.addWidget(info)
        box=QTextEdit(); box.setPlainText(body); lay.addWidget(box)
        row=QHBoxLayout(); copy=QPushButton(ui_text(self,'copy_clipboard')); close=QPushButton(ui_text(self,'close'))
        copy.clicked.connect(lambda: QApplication.clipboard().setText(box.toPlainText()))
        close.clicked.connect(dlg.accept); row.addStretch(); row.addWidget(copy); row.addWidget(close); lay.addLayout(row)
        dlg.exec(); self.accept()


class MasterRecordEditor(QDialog):
    """Graphical JSON record editor used by Master Manager."""
    def __init__(self, title, record=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(680, 620)
        self.record = dict(record or {})
        root = QVBoxLayout(self)
        intro = QLabel('Edit the selected master record. Lists can be entered as comma-separated values.')
        intro.setWordWrap(True)
        intro.setStyleSheet('color:#526579; padding:4px 0 8px 0;')
        root.addWidget(intro)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); self.form = QFormLayout(body); self.form.setLabelAlignment(Qt.AlignRight)
        self.inputs = {}
        keys = list(self.record.keys()) or ['name', 'email', 'country', 'active']
        preferred = ['serial','hospital_name','country','system','type','mr_company','magnetic_field','mr_product','insightec_owner','distributor','name','short_name','company','organization','role','class','mail','permission','active','comment','uuid']
        keys = [k for k in preferred if k in keys] + [k for k in keys if k not in preferred]
        for key in keys:
            value = self.record.get(key, '')
            if isinstance(value, bool):
                w = QCheckBox(); w.setChecked(value)
            elif isinstance(value, (list, dict)):
                w = QTextEdit(); w.setMinimumHeight(72)
                if isinstance(value, list): w.setPlainText(', '.join(str(x) for x in value))
                else: w.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                w = QLineEdit(str(value) if value is not None else '')
            self.inputs[key] = w
            self.form.addRow(key.replace('_',' ').title() + ':', w)
        scroll.setWidget(body); root.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def data(self):
        result = dict(self.record)
        for key, w in self.inputs.items():
            if isinstance(w, QCheckBox): result[key] = w.isChecked()
            elif isinstance(w, QTextEdit):
                text = w.toPlainText().strip()
                old = self.record.get(key)
                if isinstance(old, dict):
                    try: result[key] = json.loads(text) if text else {}
                    except Exception: result[key] = {'value': text}
                else: result[key] = [x.strip() for x in text.split(',') if x.strip()]
            else: result[key] = w.text().strip()
        return result


class MasterManagerDialog(QDialog):
    MASTER_SPECS = [
        ('people', 'masters/people_master.json', ['name','short_name','company','organization','role','class','mail','country','permission','active']),
        ('hospital', 'masters/hospital_master.json', ['serial','hospital_name','country','system','type','mr_company','magnetic_field','insightec_owner','distributor']),
        ('recipient', 'masters/recipients.json', ['country','to_count','member_count','source_column']),
        ('salesforce_mapping', 'profiles/salesforce_profile_default.json', ['source','salesforce_label','type']),
    ]

    def __init__(self,parent=None):
        super().__init__(parent)
        self.settings = getattr(parent, 'settings', read_json(APP_DIR/'config/settings.json', {}))
        self.setWindowTitle(ui_text(self,'master_manager'))
        self.resize(1180, 740)
        self.setMinimumSize(780, 580)
        self.datasets = {}
        self.tables = {}
        self.current_keys = {}
        self.build_ui()
        self.reload_all()

    def build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(18,18,18,18); root.setSpacing(12)
        header=QHBoxLayout()
        title=QLabel('Master Data Console'); title.setStyleSheet('font-size:24px; font-weight:700; color:#052A4F;')
        subtitle=QLabel('Search, review and maintain users, installed systems, mailing recipients and Salesforce mappings.')
        subtitle.setStyleSheet('color:#526579; font-size:13px;')
        head_text=QVBoxLayout(); head_text.addWidget(title); head_text.addWidget(subtitle)
        header.addLayout(head_text); header.addStretch()
        self.status=QLabel('Ready'); self.status.setStyleSheet('background:#E7F4FF; color:#005DAA; padding:7px 12px; border-radius:12px; font-weight:600;')
        header.addWidget(self.status); root.addLayout(header)

        cards=QHBoxLayout(); self.cards={}
        for key,label,icon in [('people','People','👥'),('hospital','Systems','🏥'),('country','Countries','🌏'),('recipient','Mail routes','✉')]:
            frame=QFrame(); frame.setStyleSheet('QFrame{background:white;border:1px solid #D7E3F1;border-radius:10px;}')
            lay=QVBoxLayout(frame); top=QLabel(f'{icon}  {label}'); top.setStyleSheet('color:#526579;font-weight:600;')
            value=QLabel('0'); value.setStyleSheet('font-size:26px;font-weight:700;color:#005DAA;')
            lay.addWidget(top); lay.addWidget(value); self.cards[key]=value; cards.addWidget(frame)
        root.addLayout(cards)

        toolbar=QHBoxLayout()
        self.search=QLineEdit(); self.search.setPlaceholderText('Search current master...'); self.search.setClearButtonEnabled(True); self.search.textChanged.connect(self.apply_filter)
        toolbar.addWidget(self.search,1)
        for text,slot in [('＋ Add',self.add_record),('Edit',self.edit_record),('Delete',self.delete_record),('Import',self.import_current),('Export',self.export_current),('Refresh',self.reload_all)]:
            b=QPushButton(text); b.clicked.connect(slot); toolbar.addWidget(b)
        root.addLayout(toolbar)

        self.tabs=QTabWidget(); self.tabs.currentChanged.connect(lambda _=0: self.apply_filter())
        for title_key,path,columns in self.MASTER_SPECS:
            page=QWidget(); lay=QVBoxLayout(page); lay.setContentsMargins(0,8,0,0)
            table=QTableWidget(); table.setColumnCount(len(columns)); table.setHorizontalHeaderLabels([c.replace('_',' ').title() for c in columns])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QTableWidget.SelectRows); table.setSelectionMode(QTableWidget.SingleSelection)
            table.setAlternatingRowColors(True); table.setSortingEnabled(True); table.doubleClicked.connect(self.edit_record)
            table.setStyleSheet('QTableWidget{background:white;alternate-background-color:#F5F8FC;border:1px solid #D7E3F1;border-radius:8px;gridline-color:#E7EEF6;} QHeaderView::section{background:#EAF3FB;color:#052A4F;font-weight:700;padding:8px;border:0;border-right:1px solid #D7E3F1;}')
            lay.addWidget(table); self.tables[title_key]=table; self.current_keys[title_key]=columns
            self.tabs.addTab(page, ui_text(self,title_key))
        root.addWidget(self.tabs,1)

        footer=QHBoxLayout(); self.detail=QLabel('Double-click a row to edit it. Changes are written directly to the master JSON files.')
        self.detail.setStyleSheet('color:#526579;'); footer.addWidget(self.detail); footer.addStretch()
        backup=QPushButton('Create Backup'); backup.clicked.connect(self.create_backup); footer.addWidget(backup)
        update_zip=QPushButton('Save update.zip'); update_zip.clicked.connect(self.create_update_zip); update_zip.setStyleSheet('background:#5B4AA0;color:white;font-weight:700;padding:8px 14px;'); footer.addWidget(update_zip)
        close=QPushButton(ui_text(self,'close')); close.clicked.connect(self.accept); footer.addWidget(close); root.addLayout(footer)

    def current_spec(self):
        idx=self.tabs.currentIndex(); return self.MASTER_SPECS[idx]

    def load_dataset(self, key, path):
        raw=read_json(APP_DIR/path, [] if key!='recipient' else {})
        if key=='recipient':
            rows=[]
            for country,info in raw.items():
                rows.append({'country':country,'to_count':len(info.get('to',[])),'member_count':len(info.get('members',[])),'source_column':info.get('source_column',''),'_raw':info})
            return rows
        if key=='salesforce_mapping': return list(raw.get('fields',[]))
        return list(raw) if isinstance(raw,list) else []

    def reload_all(self):
        for key,path,columns in self.MASTER_SPECS:
            self.datasets[key]=self.load_dataset(key,path); self.populate(key)
        people=self.datasets.get('people',[]); hospitals=self.datasets.get('hospital',[]); recipients=self.datasets.get('recipient',[])
        self.cards['people'].setText(str(len(people))); self.cards['hospital'].setText(str(len(hospitals)))
        self.cards['country'].setText(str(len({r.get('country') for r in hospitals if r.get('country')})))
        self.cards['recipient'].setText(str(len(recipients))); self.status.setText('Masters loaded and validated')

    def populate(self,key):
        table=self.tables[key]; columns=self.current_keys[key]; rows=self.datasets.get(key,[])
        table.setSortingEnabled(False); table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,col in enumerate(columns):
                value=row.get(col,'')
                if isinstance(value,bool): value='Yes' if value else 'No'
                elif isinstance(value,list): value=', '.join(str(x) for x in value)
                item=QTableWidgetItem(str(value)); item.setData(Qt.UserRole,r); table.setItem(r,c,item)
        table.setSortingEnabled(True); table.resizeRowsToContents(); table.resizeColumnsToContents()
        for c in range(table.columnCount()):
            table.setColumnWidth(c, min(max(table.columnWidth(c), 90), 260))

    def apply_filter(self):
        key,_,_=self.current_spec(); table=self.tables[key]; term=self.search.text().strip().lower(); shown=0
        for row in range(table.rowCount()):
            match=not term or any(term in (table.item(row,c).text().lower() if table.item(row,c) else '') for c in range(table.columnCount()))
            table.setRowHidden(row,not match); shown += int(match)
        self.status.setText(f'{shown} record(s) shown')

    def selected_index(self):
        key,_,_=self.current_spec(); table=self.tables[key]; row=table.currentRow()
        if row<0: return key,None
        item=table.item(row,0); return key,(item.data(Qt.UserRole) if item else row)

    def add_record(self):
        key,path,_=self.current_spec()
        if key=='recipient': QMessageBox.information(self,'Mail routes','Add a country by importing an updated mailing master.'); return
        if key == 'salesforce_mapping':
            seed = {'source':'','salesforce_label':'','type':'text'}
        elif key == 'people':
            seed = {
                'uuid': str(uuid.uuid4()),
                'company': '',
                'organization': '',
                'name': '',
                'short_name': '',
                'role': '',
                'class': '',
                'mail': '',
                'country': '',
                'permission': 'User',
                'comment': '',
                'active': True,
            }
        elif key == 'hospital':
            seed = {
                'serial': '', 'hospital_name': '', 'country': '', 'system': '',
                'type': '', 'mr_company': '', 'magnetic_field': '', 'mr_product': '',
                'insightec_owner': '', 'distributor': ''
            }
        else:
            seed = {}
        dlg=MasterRecordEditor('Add Record',seed,self)
        if dlg.exec(): self.datasets[key].append(dlg.data()); self.save_dataset(key,path); self.populate(key); self.update_cards()

    def edit_record(self,*_):
        key,idx=self.selected_index()
        if idx is None: QMessageBox.information(self,'Edit','Select a row first.'); return
        path=next(p for k,p,_ in self.MASTER_SPECS if k==key); record=self.datasets[key][idx]
        if key=='recipient':
            country=record['country']; all_data=read_json(APP_DIR/path,{}); raw=all_data.get(country,{})
            dlg=MasterRecordEditor(f'Edit Mail Route - {country}',raw,self)
            if dlg.exec(): all_data[country]=dlg.data(); write_json(APP_DIR/path,all_data); self.reload_all()
            return
        dlg=MasterRecordEditor('Edit Record',record,self)
        if dlg.exec(): self.datasets[key][idx]=dlg.data(); self.save_dataset(key,path); self.populate(key); self.update_cards()

    def delete_record(self):
        key,idx=self.selected_index()
        if idx is None: return
        if QMessageBox.question(self,'Delete','Delete the selected master record?',QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes: return
        path=next(p for k,p,_ in self.MASTER_SPECS if k==key)
        if key=='recipient':
            country=self.datasets[key][idx]['country']; raw=read_json(APP_DIR/path,{}); raw.pop(country,None); write_json(APP_DIR/path,raw)
        else:
            self.datasets[key].pop(idx); self.save_dataset(key,path)
        self.reload_all()

    def save_dataset(self,key,path):
        if key=='salesforce_mapping':
            raw=read_json(APP_DIR/path,{}); raw['fields']=self.datasets[key]; write_json(APP_DIR/path,raw)
        else: write_json(APP_DIR/path,self.datasets[key])
        self.status.setText('Saved')

    def update_cards(self):
        self.reload_all()

    def import_current(self):
        key,path,_=self.current_spec(); fn,_=QFileDialog.getOpenFileName(self,'Import Master',str(APP_DIR),'JSON (*.json);;Excel (*.xlsx);;CSV (*.csv);;All (*.*)')
        if not fn:return
        if fn.lower().endswith('.json'):
            try:
                data=json.load(open(fn,encoding='utf-8')); write_json(APP_DIR/path,data); self.reload_all(); QMessageBox.information(self,'Import','Master imported successfully.')
            except Exception as e: QMessageBox.warning(self,ui_text(self,'error'),str(e))
        else: QMessageBox.information(self,ui_text(self,'import_title'),ui_text(self,'import_prepared'))

    def export_current(self):
        key,path,_=self.current_spec(); suggested=f'{key}_master_export.json'; fn,_=QFileDialog.getSaveFileName(self,'Export Master',str(APP_DIR/suggested),'JSON (*.json)')
        if not fn:return
        shutil.copy2(APP_DIR/path,fn); self.status.setText(f'Exported: {Path(fn).name}')

    def create_backup(self):
        out=APP_DIR/'backups'/f'masters_{datetime.datetime.now():%Y%m%d_%H%M%S}.zip'; out.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for _,path,_ in self.MASTER_SPECS:
                f=APP_DIR/path
                if f.exists(): z.write(f,path)
        QMessageBox.information(self,'Backup',f'Backup created:\n{out}')

    def create_update_zip(self):
        """Export administrator-maintained data as an importable master update package."""
        default_name=f'Complaint_Service_Hub_Master_Update_{datetime.datetime.now():%Y%m%d_%H%M%S}.zip'
        fn,_=QFileDialog.getSaveFileName(self,'Save Master Update ZIP',str(APP_DIR/default_name),'ZIP (*.zip)')
        if not fn:
            return
        if not fn.lower().endswith('.zip'):
            fn += '.zip'
        include_roots=('masters','templates','profiles')
        files=[]
        for root_name in include_roots:
            root=APP_DIR/root_name
            if root.exists():
                files.extend(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        manifest={
            'package_type':'master_update',
            'format_version':1,
            'created_at':datetime.datetime.now().isoformat(timespec='seconds'),
            'created_by':self.settings.get('actual_user') or self.settings.get('user',''),
            'source_build':read_json(APP_DIR/'version.json',{}).get('build',''),
            'files':[str(p.relative_to(APP_DIR)).replace('\\','/') for p in files],
            'notes':'Administrator-maintained user, system, recipient, complaint input list, template and profile data.'
        }
        try:
            with zipfile.ZipFile(fn,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('complaint_service_hub/update_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
                for f in files:
                    rel=str(f.relative_to(APP_DIR)).replace('\\','/')
                    z.write(f,'complaint_service_hub/'+rel)
            self.status.setText(f'Update ZIP saved: {Path(fn).name}')
            QMessageBox.information(self,'Master Update ZIP',f'Importable update ZIP created successfully:\n{fn}\n\nFiles: {len(files)}')
        except Exception as e:
            QMessageBox.warning(self,'Master Update ZIP',f'Could not create update ZIP:\n{e}')

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent); self.settings=settings; self.setWindowTitle(ui_text(self,'settings')); self.resize(480,320)
        lay=QVBoxLayout(self); form=QFormLayout(); self.lang=QComboBox(); [self.lang.addItem(v,k) for k,v in LANG_NAMES.items()]; self.out=QComboBox(); self.out.addItems(['Outlook','Template']); self.auto=QCheckBox(ui_text(self,'auto_login'))
        self.lang.setCurrentIndex(max(0,self.lang.findData(settings.get('language','en')))); self.out.setCurrentText(settings.get('output_mode','Outlook')); self.auto.setChecked(settings.get('auto_login',False))
        form.addRow(ui_text(self,'language'),self.lang); form.addRow(ui_text(self,'output_mode'),self.out); form.addRow('',self.auto); lay.addLayout(form)
        btn=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); btn.accepted.connect(self.save); btn.rejected.connect(self.reject); lay.addWidget(btn)
    def save(self):
        self.settings['language']=self.lang.currentData(); self.settings['output_mode']=self.out.currentText(); self.settings['auto_login']=self.auto.isChecked(); write_json(APP_DIR/'config/settings.json', self.settings); self.accept()

class MainWindow(QMainWindow):
    def __init__(self, settings, people):
        super().__init__()
        self.settings=settings; self.people=people; self.master_cache={}; self.trans=read_json(APP_DIR/'masters/translations.json', {})
        self.version=read_json(APP_DIR/'app_version.json', {})
        self.admin_mode=bool(settings.get('startup_admin', False))
        self._switching_user = False
        self._allow_close = False
        self.setWindowTitle('InSightec Complaint Service Hub')
        self.resize(1250,780)
        self.setStyleSheet(f'''
            QMainWindow{{background:{BG};}}
            QWidget{{font-size:15px;}}
            QLabel{{color:#1E2937; font-size:15px;}}
            QPushButton{{cursor:pointer; font-size:15px; min-height:34px; padding:6px 11px;}}
            QLineEdit, QComboBox, QDateEdit{{font-size:15px; min-height:34px; padding:4px 7px;}}
            QTextEdit, QListWidget, QTableWidget{{font-size:15px;}}
            QGroupBox{{font-size:17px;}}
        ''')
        self.build_ui()
        self.retranslate()
        self.guide_manager = GuideManager(self, APP_DIR, self.settings.get('language', 'en'))
        self._master_loader = MasterDataLoader(self); self._master_loader.loaded.connect(self._on_master_loaded); self._master_loader.failed.connect(lambda e: log('Master background load failed: '+e)); self._master_loader.start()
    def _on_master_loaded(self, payload):
        self.master_cache = payload
        if payload.get('translations.json'):
            self.trans = payload['translations.json']
        log('Master data background load completed.')

    def t(self,k):
        lang=self.settings.get('language','en')
        return self.trans.get(lang,self.trans.get('en',{})).get(k,k)
    def current_person(self):
        selected = self.settings.get('company','')
        name = self.settings.get('user','')
        if selected == 'InSightec':
            return next((p for p in self.people if p.get('name') == name and p.get('company') == 'InSightec'), {})
        selected_org = selected_company_org(selected)
        return next((p for p in self.people if p.get('name') == name and p.get('company') == 'Distributor' and p.get('organization') == selected_org), {})
    def is_masaki(self):
        return 'masaki' in self.settings.get('user','').lower()
    def is_insightec(self): return self.settings.get('company')=='InSightec'
    def is_admin_eligible(self):
        person = self.current_person()
        return self.is_insightec() and person.get('permission') in ('Admin', 'Super User')
    def build_ui(self):
        central=QWidget(); self.setCentralWidget(central); root=QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        self.nav=QFrame(); self.nav.setFixedWidth(255); self.nav.setStyleSheet(f'QFrame{{background:{DARK};}} QLabel{{color:white;}} QPushButton{{color:white; background:transparent; border:0; text-align:left; padding:10px 16px; font-size:16px;}} QPushButton:hover{{background:#0B5D9A;}}')
        navlay=QVBoxLayout(self.nav); navlay.setContentsMargins(18,22,18,18)
        logo=QLabel('InSightec'); logo.setFont(QFont('Arial',26,QFont.Bold)); logo.setStyleSheet('color:white; font-style:italic;')
        navlay.addWidget(logo); sub=QLabel('Bringing therapy into focus'); sub.setStyleSheet('color:#DCEBFF;'); navlay.addWidget(sub)
        badge=QLabel(f"Complaint Service Hub\n{self.version.get('program','0.5 Alpha')} · Build {self.version.get('build','')}"); badge.setStyleSheet(f'background:#073B70; border:1px solid {ACCENT}; border-radius:8px; padding:12px; color:white; font-weight:bold;'); badge.setMinimumHeight(70); navlay.addWidget(badge); navlay.addSpacing(10)
        self.nav_buttons=[]
        for key, icon in [('home','🏠'),('complaint','📝'),('salesforce','☁'),('update_zip','📦'),('settings','⚙'),('guide','❔'),('feedback','💬'),('system_no','➕'),('master_manager','🛠'),('log_viewer','📋'),('about','ⓘ')]:
            b=QPushButton(f'{icon}  {key}'); b.clicked.connect(lambda checked=False,k=key: self.open_tool(k)); self.nav_buttons.append((key,b)); navlay.addWidget(b)
        navlay.addStretch(); self.footer=QLabel('© InSightec'); self.footer.setStyleSheet('color:#DCEBFF;'); navlay.addWidget(self.footer)
        root.addWidget(self.nav)
        self.main=QWidget(); mainlay=QVBoxLayout(self.main); mainlay.setContentsMargins(28,24,28,10); mainlay.setSpacing(12)
        head=QHBoxLayout(); self.title=QLabel(); self.title.setFont(QFont('Arial',25,QFont.Bold)); self.title.setStyleSheet(f'color:{PRIMARY};')
        self.subtitle=QLabel(); self.subtitle.setFont(QFont('Arial',25,QFont.Bold));
        head.addWidget(self.title); head.addWidget(self.subtitle); head.addSpacing(10); self.version_label=QLabel(); head.addWidget(self.version_label); head.addStretch()
        self.lang_cb=QComboBox(); [self.lang_cb.addItem(name,code) for code,name in LANG_NAMES.items()]; self.lang_cb.setCurrentIndex(max(0,self.lang_cb.findData(self.settings.get('language','en')))); self.lang_cb.currentIndexChanged.connect(self.change_lang)
        self.user_label=QLabel(); self.admin_btn=QPushButton(ui_text(self,'admin_mode_off')); self.admin_btn.clicked.connect(self.toggle_admin); self.admin_btn.setVisible(self.is_admin_eligible())
        self.logout_btn=QPushButton(self.t('logout')); self.logout_btn.clicked.connect(self.logout_and_switch_user)
        self.language_label=QLabel(self.t('language'))
        for w in [self.language_label, self.lang_cb, self.user_label, self.admin_btn, self.logout_btn]: head.addWidget(w)
        mainlay.addLayout(head)
        self.info=QLabel(); mainlay.addWidget(self.info)
        line=QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet(f'color:{CARD_BORDER};'); mainlay.addWidget(line)
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.NoFrame)
        self.content=QWidget(); self.grid=QGridLayout(self.content); self.grid.setContentsMargins(4,4,4,20); self.grid.setHorizontalSpacing(22); self.grid.setVerticalSpacing(22)
        self.scroll.setWidget(self.content); mainlay.addWidget(self.scroll,1)
        self.status=QLabel(); self.status.setStyleSheet(f'background:{DARK}; color:white; padding:8px; border-radius:4px;'); mainlay.addWidget(self.status)
        root.addWidget(self.main,1)
        self.refresh_cards()
    def allowed_tools(self):
        base=['complaint','update_zip','settings','guide','feedback','system_no']
        if self.is_insightec(): base.insert(1,'salesforce')
        if self.is_admin_eligible() and self.admin_mode: base += ['master_manager','log_viewer','about']
        return base
    def refresh_cards(self):
        while self.grid.count():
            item=self.grid.takeAt(0); w=item.widget();
            if w: w.deleteLater()
        allowed=self.allowed_tools()
        defs={
            'complaint':('Complaint','Create complaint, check English, generate Outlook mail or copy template.','📝',PRIMARY,'User tool'),
            'salesforce':('Salesforce','Auto input mapped complaint fields to Salesforce on Microsoft Edge.','☁','#10883E','InSightec user'),
            'update_zip':('Update ZIP','Load Master Update or Program Update ZIP. Backup is created automatically.','📦','#D26900','User tool'),
            'settings':('Settings','Default country, output mode, language and paths.','⚙','#008B8B','Available to all users'),
            'guide':('Guide','Open the quick guide and guided tour.','❔','#005DAA','Available to all users'),
            'feedback':('Feedback','Send bug reports, improvement requests, questions, screenshots, logs, and validation reports.','💬','#1E88E5','User tool'),
            'system_no':('System No.','Create a system-number addition request.','➕','#198754','User tool'),
            'master_manager':('Master Manager','Edit masters and create update ZIP package.','🛠','#5B4AA0','Admin only'),
            'log_viewer':('Log Viewer','View application logs and operation history.','📋','#1E88E5','Admin only'),
            'about':('About','Application information and version.','ⓘ','#333333','Admin only')}
        row=0; col=0
        title=QLabel(self.t('launch_pad')); title.setFont(QFont('Arial',18,QFont.Bold)); self.grid.addWidget(title,row,0,1,3); row+=1
        for k in allowed:
            title,desc,icon,color,tag=defs[k]
            c=ToolCard(self.t(k) if k in self.trans.get(self.settings.get('language','en'),{}) else title, self.t(k+'_desc'), icon, color, self.t(k+'_tag'), lambda key=k: self.open_tool(key), self.t('start'))
            self.grid.addWidget(c,row,col)
            col+=1
            if col>=3: col=0; row+=1
        if self.is_admin_eligible() and self.admin_mode:
            admin=QLabel(self.t('admin_only')); admin.setFont(QFont('Arial',15,QFont.Bold)); admin.setStyleSheet('color:#5B4AA0;'); self.grid.addWidget(admin,row,0,1,3)
    def retranslate(self):
        self.title.setText('InSightec')
        self.subtitle.setText('Complaint Service Hub')
        self.version_label.setText(f"{self.version.get('program','0.5 Alpha')} · Build {self.version.get('build','')}")
        self.info.setText(f"{self.t('company')}: {self.settings.get('company')}  |  {self.t('language')}: {LANG_NAMES.get(self.settings.get('language'),'English')}")
        self.user_label.setText(self.settings.get('user',''))
        self.language_label.setText(self.t('language'))
        self.admin_btn.setText(self.t('admin_mode_on') if self.admin_mode else self.t('admin_mode_off'))
        self.logout_btn.setText(self.t('logout'))
        self.status.setText(f"{self.t('ready')}  |  Program {self.version.get('program')} Build {self.version.get('build')}  |  Master {self.version.get('master')}  |  User {self.settings.get('user')}")
        for key,b in self.nav_buttons:
            b.setVisible(key in ['home']+self.allowed_tools())
            b.setText(f"{b.text().split('  ')[0]}  {self.t(key)}")
        self.refresh_cards()
    def change_output(self, text):
        self.settings['output_mode']=text; write_json(APP_DIR/'config/settings.json', self.settings); self.retranslate()
    def change_lang(self):
        self.settings['language']=self.lang_cb.currentData(); write_json(APP_DIR/'config/settings.json', self.settings); self.retranslate()
        if hasattr(self, 'guide_manager'):
            self.guide_manager.set_language(self.settings.get('language', 'en'))
    def toggle_admin(self):
        if not self.is_admin_eligible():
            return
        if not self.admin_mode:
            expected=str(self.settings.get('admin_password','5963'))
            for attempt in range(3):
                password,ok=QInputDialog.getText(self,'Admin Mode Authentication','Enter the Admin Mode password:',QLineEdit.Password)
                if not ok:
                    return
                if password == expected:
                    self.admin_mode=True
                    break
                remaining=2-attempt
                if remaining:
                    QMessageBox.warning(self,'Admin Mode','Incorrect password. Please try again.')
                else:
                    QMessageBox.critical(self,'Admin Mode','Incorrect password. Admin Mode was not enabled.')
                    return
        else:
            self.admin_mode=False
        self.admin_btn.setText(self.t('admin_mode_on') if self.admin_mode else self.t('admin_mode_off'))
        self.admin_btn.setStyleSheet('background:#E6A700; padding:8px;' if self.admin_mode else '')
        self.retranslate()
    def logout_and_switch_user(self):
        """End the current session and reopen the startup selector without exiting the app."""
        if QMessageBox.question(self, self.t('logout'), self.t('logout_confirm')) != QMessageBox.Yes:
            return
        session = dict(self.settings)
        session['auto_login'] = False
        session['startup_admin'] = False
        dlg = StartupDialog(session, self.people)
        if dlg.exec() != QDialog.Accepted:
            return
        write_json(APP_DIR/'config/settings.json', session)
        self._next_window = MainWindow(session, self.people)
        self._next_window.show()
        self._switching_user = True
        self.close()

    def open_tool(self, key):
        log(f'Open tool requested: {key!r}')
        try:
            if key=='home':
                self.refresh_cards()
                self.scroll.verticalScrollBar().setValue(0)
            elif key=='complaint': ComplaintDialog(self).exec()
            elif key=='guide': self.guide_manager.show_guide()
            elif key=='settings':
                if SettingsDialog(self.settings,self).exec():
                    self.lang_cb.setCurrentIndex(max(0,self.lang_cb.findData(self.settings.get('language','en')))); self.retranslate()
            elif key=='update_zip': self.apply_update_zip()
            elif key=='feedback': FeedbackDialog(self).exec()
            elif key=='master_manager': MasterManagerDialog(self).exec()
            elif key=='salesforce': SalesforceWorkflowDialog(self).exec()
            elif key=='log_viewer': self.show_logs()
            elif key=='about': QMessageBox.information(self,self.t('about'),f"InSightec Complaint Service Hub\n{self.t('program')}: {self.version.get('program')}\n{self.t('build')}: {self.version.get('build')}\n{self.t('architecture_note')}")
            elif key=='system_no': QMessageBox.information(self,self.t('system_no'), self.t('system_no_prepared'))
            else:
                raise ValueError(f'Unknown tool key: {key!r}')
            log(f'Open tool completed: {key!r}')
        except Exception as exc:
            log(f'Open tool failed: key={key!r}, error={exc!r}')
            QMessageBox.critical(self, self.t('launch_error'), self.t('function_start_failed') + f'\n\nTool: {key}\nError: {exc}')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'guide_manager') and self.guide_manager.overlay.isVisible():
            self.guide_manager.overlay.setGeometry(self.rect())

    def closeEvent(self, event):
        if self._switching_user or self._allow_close:
            event.accept()
            return
        accepted, show_next = self.guide_manager.confirm_exit()
        if not accepted:
            event.ignore()
            return
        if show_next:
            self.guide_manager.reset_for_next_startup()
        self._allow_close = True
        event.accept()

    def apply_update_zip(self):
        fn,_=QFileDialog.getOpenFileName(self,self.t('select_update_zip'),str(APP_DIR),self.t('zip_files_filter'))
        if not fn: return
        # detect manifest type
        try:
            with zipfile.ZipFile(fn) as z:
                names=z.namelist(); text='\n'.join(names).lower()
                is_program=('hub_app.py' in text) or ('launcher.py' in text) or ('updater.py' in text) or ('program_update' in text)
        except Exception as e:
            QMessageBox.warning(self,self.t('update'),str(e)); return
        if is_program:
            dst=APP_DIR/'updates'/'pending_program_update.zip'; dst.parent.mkdir(exist_ok=True); shutil.copy2(fn,dst)
            QMessageBox.information(self,self.t('program_update'),self.t('program_update_staged'))
        else:
            self.apply_master_update(Path(fn))
    def apply_master_update(self, path):
        bdir=APP_DIR/'backups'/f"master_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}"; bdir.mkdir(parents=True,exist_ok=True)
        try:
            with zipfile.ZipFile(path) as z:
                for n in z.namelist():
                    if n.endswith('/'): continue
                    rel=n
                    if rel.startswith('complaint_service_hub/'): rel=rel[len('complaint_service_hub/'):]
                    if not (rel.startswith('masters/') or rel.startswith('templates/') or rel.startswith('profiles/') or rel.startswith('config/')): continue
                    dst=APP_DIR/rel
                    if dst.exists():
                        (bdir/rel).parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dst,bdir/rel)
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(n) as src, open(dst,'wb') as out: shutil.copyfileobj(src,out)
            QMessageBox.information(self,self.t('master_update'),self.t('master_update_completed'))
        except Exception as e: QMessageBox.warning(self,self.t('master_update_failed'),str(e))
    def show_logs(self):
        dlg=QDialog(self); dlg.setWindowTitle(self.t('log_viewer')); dlg.resize(800,550); lay=QVBoxLayout(dlg); box=QTextEdit(); box.setReadOnly(True); content=''
        for p in sorted((APP_DIR/'logs').glob('*.log')):
            content += f'===== {p.name} =====\n' + p.read_text(encoding='utf-8', errors='ignore')[-4000:] + '\n\n'
        box.setPlainText(content or self.t('no_logs_yet')); lay.addWidget(box); b=QPushButton(self.t('close')); b.clicked.connect(dlg.accept); lay.addWidget(b); dlg.exec()

def main():
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING','1')
    os.environ.setdefault('QT_SCALE_FACTOR_ROUNDING_POLICY','PassThrough')
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass
    app=QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont('Arial', 11))
    app.setStyleSheet('QLineEdit,QComboBox,QDateEdit,QPushButton{min-height:28px;} QToolTip{font-size:11px;}')
    settings=read_json(APP_DIR/'config/settings.json', {})
    people=read_json(APP_DIR/'masters/people_master.json', [])
    if not settings.get('auto_login'):
        dlg=StartupDialog(settings, people)
        if dlg.exec() != QDialog.Accepted:
            return 0
        # auto language by selected user's country when language not manually changed
        person=dlg.selected_person(); country=person.get('country','')
        if country and settings.get('language') not in LANG_NAMES:
            settings['language']=COUNTRY_DEFAULT_LANG.get(country,'en')
        write_json(APP_DIR/'config/settings.json', settings)
    win=MainWindow(settings, people); win.show()
    from PySide6.QtCore import QTimer
    QTimer.singleShot(250, win.guide_manager.show_startup_prompt)
    return app.exec()

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        import traceback
        error_log = APP_DIR / 'logs' / 'hub_startup_error.log'
        error_log.parent.mkdir(parents=True, exist_ok=True)
        error_log.write_text(traceback.format_exc(), encoding='utf-8')
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                'Complaint Service Hub - Startup Error',
                f'The application could not start.\n\n{exc}\n\nDiagnostic log:\n{error_log}',
            )
        except Exception:
            pass
        raise
