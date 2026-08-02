import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QCheckBox,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QPlainTextEdit
)

APP_TITLE = 'File Type ZIP Builder & Test'


def read_lines(path: Path):
    for enc in ('utf-8-sig', 'utf-8', 'cp932', 'shift_jis', 'latin-1'):
        try:
            return path.read_text(encoding=enc, errors='strict').splitlines()
        except Exception:
            pass
    return path.read_text(encoding='utf-8', errors='replace').splitlines()


def safe_id(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', text.strip()) or 'new_plugin'


def parse_filename_date(path: Path):
    months = {m.lower(): i for i, m in enumerate(
        ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}
    m = re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[_-]+(?P<mon>[A-Za-z]{3})[_-]+(?P<d>\d{1,2})[_-]+\d{1,2}[_-]+\d{1,2}[_-]+\d{1,2}[_-]+(?P<y>20\d{2})', path.name)
    if not m:
        return None
    try:
        return datetime(int(m.group('y')), months[m.group('mon').lower()], int(m.group('d')))
    except Exception:
        return None


def test_structured_file(path: Path, parser: dict) -> dict:
    lines = read_lines(path)
    header_re = re.compile(parser['header_line_regex'])
    data_re = re.compile(parser['data_line_regex'])
    columns = list(parser.get('columns') or [])
    parsed = []
    errors = []
    for line_no, line in enumerate(lines, 1):
        hm = header_re.search(line)
        if hm:
            text = hm.groupdict().get(parser.get('columns_group', 'columns')) or (hm.group(1) if hm.groups() else '')
            found = [x for x in re.split(r'\s+', text.strip()) if x]
            if found:
                columns = found
            continue
        dm = data_re.search(line.strip())
        if not dm:
            continue
        gd = dm.groupdict()
        values = [x for x in re.split(r'\s+', gd.get(parser.get('values_group', 'values'), '').strip()) if x]
        if not columns:
            errors.append(f'Line {line_no}: data found before header')
            continue
        if len(values) != len(columns):
            errors.append(f'Line {line_no}: expected {len(columns)} values, got {len(values)}')
        row = {'Timestamp': gd.get(parser.get('time_group', 'time'), '')}
        for i, col in enumerate(columns):
            if i >= len(values):
                break
            try:
                row[col] = float(values[i])
            except Exception:
                row[col] = values[i]
        parsed.append(row)
    return {
        'sample': path.name,
        'columns': columns,
        'parsed_rows': len(parsed),
        'errors': errors[:100],
        'first_rows': parsed[:5],
        'passed': bool(parsed) and not errors,
    }


class PluginBuilder(QWidget):
    def __init__(self):
        super().__init__()
        self.samples: list[Path] = []
        self.last_report = None
        self.setWindowTitle(APP_TITLE)
        self.resize(1050, 820)
        self.build_ui()
        self.apply_preset('VIMeasure')

    def build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel(APP_TITLE)
        title.setStyleSheet('font-size:20px;font-weight:bold;')
        root.addWidget(title)
        note = QLabel('Create, validate and test a File Type Update ZIP before installing it in Log Merge Tool.')
        note.setWordWrap(True)
        root.addWidget(note)

        top = QHBoxLayout()
        top.addWidget(QLabel('Preset'))
        self.preset = QComboBox(); self.preset.addItems(['VIMeasure', 'Blank Structured Table'])
        top.addWidget(self.preset); top.addStretch(1)
        root.addLayout(top)

        form_box = QGroupBox('Plugin Information')
        form = QFormLayout(form_box)
        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.version_edit = QLineEdit('1.0.0')
        self.patterns_edit = QLineEdit()
        self.merge_chk = QCheckBox('Allow Merge'); self.merge_chk.setChecked(True)
        self.import_chk = QCheckBox('Allow Import'); self.import_chk.setChecked(True)
        self.hover_chk = QCheckBox('Enable hover popup')
        form.addRow('Plugin ID', self.id_edit)
        form.addRow('Display Name', self.name_edit)
        form.addRow('Version', self.version_edit)
        form.addRow('File Patterns', self.patterns_edit)
        mode = QWidget(); mode_l = QHBoxLayout(mode); mode_l.setContentsMargins(0,0,0,0)
        for w in [self.merge_chk, self.import_chk, self.hover_chk]: mode_l.addWidget(w)
        mode_l.addStretch(1)
        form.addRow('Capabilities', mode)
        root.addWidget(form_box)

        parser_box = QGroupBox('Structured Parser')
        pf = QFormLayout(parser_box)
        self.header_regex = QLineEdit()
        self.data_regex = QLineEdit()
        self.visible_columns = QLineEdit()
        self.investigation_profile = QComboBox(); self.investigation_profile.addItems(['Sonication', 'Water', 'MR', 'Initial', 'Custom'])
        pf.addRow('Header Line Regex', self.header_regex)
        pf.addRow('Data Line Regex', self.data_regex)
        pf.addRow('Default Visible Columns', self.visible_columns)
        pf.addRow('Investigation Profile', self.investigation_profile)
        root.addWidget(parser_box)

        sample_box = QGroupBox('Samples and Parser Tests')
        sl = QVBoxLayout(sample_box)
        row = QHBoxLayout()
        self.add_samples_btn = QPushButton('Add Sample Logs')
        self.clear_samples_btn = QPushButton('Clear Samples')
        self.run_tests_btn = QPushButton('Run Tests')
        row.addWidget(self.add_samples_btn); row.addWidget(self.clear_samples_btn); row.addWidget(self.run_tests_btn); row.addStretch(1)
        sl.addLayout(row)
        self.preview = QTableWidget(0, 5)
        self.preview.setHorizontalHeaderLabels(['Sample', 'Rows', 'Columns', 'Errors', 'Result'])
        self.preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sl.addWidget(self.preview)
        self.report_text = QPlainTextEdit(); self.report_text.setReadOnly(True); self.report_text.setMaximumHeight(190)
        sl.addWidget(self.report_text)
        root.addWidget(sample_box, 1)

        buttons = QHBoxLayout()
        self.build_btn = QPushButton('Build Tested Plugin ZIP')
        self.close_btn = QPushButton('Close')
        buttons.addStretch(1); buttons.addWidget(self.build_btn); buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

        self.preset.currentTextChanged.connect(self.apply_preset)
        self.add_samples_btn.clicked.connect(self.add_samples)
        self.clear_samples_btn.clicked.connect(self.clear_samples)
        self.run_tests_btn.clicked.connect(self.run_tests)
        self.build_btn.clicked.connect(self.build_zip)
        self.close_btn.clicked.connect(self.close)

    def apply_preset(self, name):
        if name == 'VIMeasure':
            self.id_edit.setText('vimeasure')
            self.name_edit.setText('VIMeasure')
            self.patterns_edit.setText('VIMeasure_*.txt')
            self.header_regex.setText(r'^;\s*Data:\s*(?P<columns>.+)$')
            self.data_regex.setText(r'^(?P<time>\d{1,2}:\d{2}:\d{2}:\d{3})\s+(?P<values>.+)$')
            self.visible_columns.setText('Timestamp,4vI,4vV,-6vI,-6vV,6vI,6vV')
            self.investigation_profile.setCurrentText('Sonication')
            self.hover_chk.setChecked(False)
        else:
            self.id_edit.setText('new_structured_log')
            self.name_edit.setText('New Structured Log')
            self.patterns_edit.setText('*.txt')
            self.header_regex.setText(r'^#\s*Data:\s*(?P<columns>.+)$')
            self.data_regex.setText(r'^(?P<time>\d{1,2}:\d{2}:\d{2}(?::\d+)?)\s+(?P<values>.+)$')
            self.visible_columns.setText('Timestamp,Value1')

    def add_samples(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select sample logs', str(Path.home()), 'Log files (*.txt *.log);;All files (*.*)')
        for f in files:
            p = Path(f)
            if p not in self.samples: self.samples.append(p)
        self.run_tests()

    def clear_samples(self):
        self.samples.clear(); self.preview.setRowCount(0); self.report_text.clear(); self.last_report = None

    def parser_definition(self):
        return {
            'format': 'structured_whitespace',
            'timestamp_mode': 'filename_date_plus_line_time',
            'header_line_regex': self.header_regex.text().strip(),
            'data_line_regex': self.data_regex.text().strip(),
            'columns_group': 'columns', 'time_group': 'time', 'values_group': 'values',
            'columns_from_header': True,
        }

    def run_tests(self):
        if not self.samples:
            QMessageBox.information(self, 'Tests', 'Add at least one sample log.')
            return False
        parser = self.parser_definition()
        results = []
        try:
            re.compile(parser['header_line_regex']); re.compile(parser['data_line_regex'])
        except Exception as exc:
            QMessageBox.critical(self, 'Regex Error', str(exc)); return False
        for p in self.samples:
            results.append(test_structured_file(p, parser))
        passed = all(r['passed'] for r in results)
        self.last_report = {
            'plugin_id': safe_id(self.id_edit.text()),
            'generated_at': datetime.now().isoformat(timespec='seconds'),
            'passed': passed,
            'sample_count': len(results),
            'results': results,
        }
        self.preview.setRowCount(len(results))
        for row, r in enumerate(results):
            vals = [r['sample'], r['parsed_rows'], len(r['columns']), len(r['errors']), 'PASS' if r['passed'] else 'FAIL']
            for c, v in enumerate(vals): self.preview.setItem(row, c, QTableWidgetItem(str(v)))
        self.report_text.setPlainText(json.dumps(self.last_report, ensure_ascii=False, indent=2))
        return passed

    def build_zip(self):
        if not self.run_tests():
            QMessageBox.warning(self, 'Build Blocked', 'All sample parser tests must pass before building the ZIP.')
            return
        pid = safe_id(self.id_edit.text())
        patterns = [p.strip() for p in re.split(r'[;,]', self.patterns_edit.text()) if p.strip()]
        modes = []
        if self.merge_chk.isChecked(): modes.append('merge')
        if self.import_chk.isChecked(): modes.append('import')
        manifest = {
            'id': pid, 'display_name': self.name_edit.text().strip() or pid,
            'version': self.version_edit.text().strip() or '1.0.0',
            'mode': modes or ['import'], 'patterns': patterns or ['*.txt'],
            'enabled': True, 'plugin_api': '2.1',
            'hover_popup': self.hover_chk.isChecked(),
            'structured_fields': True,
            'description': 'Generated and tested by File Type ZIP Builder',
        }
        parser = self.parser_definition()
        visible = [x.strip() for x in self.visible_columns.text().split(',') if x.strip()]
        viewer_defaults = {
            'default_visible_columns': visible,
            'auto_fit_on_load': True,
            'hover_popup': self.hover_chk.isChecked(),
            'numeric_columns_from_header': True,
        }
        investigation = {
            'profiles': [self.investigation_profile.currentText().lower()],
            'required_for': ['sonication'] if pid == 'vimeasure' else [],
            'display_modes': ['logs', 'chart', 'logs_and_chart'],
            'chart_series_from_numeric_columns': True,
        }
        out, _ = QFileDialog.getSaveFileName(self, 'Save tested plugin ZIP', str(Path.home() / f'{pid}.plugin.zip'), 'Plugin ZIP (*.plugin.zip *.zip)')
        if not out: return
        outp = Path(out)
        if not outp.name.lower().endswith('.zip'): outp = outp.with_suffix('.plugin.zip')
        with zipfile.ZipFile(outp, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))
            zf.writestr('parser.json', json.dumps(parser, indent=2, ensure_ascii=False))
            zf.writestr('viewer_defaults.json', json.dumps(viewer_defaults, indent=2, ensure_ascii=False))
            zf.writestr('investigation_profile.json', json.dumps(investigation, indent=2, ensure_ascii=False))
            zf.writestr('tests/test_report.json', json.dumps(self.last_report, indent=2, ensure_ascii=False))
            zf.writestr('tests/README.txt', 'The plugin ZIP was built only after all included sample parser tests passed.\n')
            zf.writestr('README.txt', 'Install from Log Merge Tool > Update File Type. Validate, install, reload, then test Smart Discovery and Viewer.\n')
            for p in self.samples:
                zf.write(p, 'sample/' + p.name)
        QMessageBox.information(self, 'Plugin ZIP', f'Created tested plugin ZIP:\n{outp}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = PluginBuilder(); w.show()
    sys.exit(app.exec())
