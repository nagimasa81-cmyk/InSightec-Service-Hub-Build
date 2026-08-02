from pathlib import Path

try:
    from PySide6.QtCore import QObject, Signal, QTimer
    from PySide6.QtWidgets import QLineEdit, QTextEdit, QComboBox, QDateEdit, QFormLayout, QLabel
except Exception:
    QObject = object
    Signal = None

VALID_STYLE = 'border:1px solid #60A870; background:#F3FFF5;'
INVALID_STYLE = 'border:1px solid #D85858; background:#FFF5F5;'
FOCUS_STYLE = 'border:2px solid #1D76D2; background:#EEF7FF;'


def widget_value(widget):
    if isinstance(widget, QLineEdit):
        return widget.text().strip()
    if isinstance(widget, QTextEdit):
        return widget.toPlainText().strip()
    if isinstance(widget, QComboBox):
        value = widget.currentText().strip()
        return '' if value in ('--None--', 'None') else value
    if isinstance(widget, QDateEdit):
        return '' if widget.date() == widget.minimumDate() else widget.date().toString('yyyy-MM-dd')
    return ''


class ValidationManager(QObject):
    """Reusable real-time required-field validation for PySide6 forms."""
    changed = Signal(dict) if Signal else None

    def __init__(self, parent=None, value_reader=None):
        super().__init__(parent)
        self._fields = {}
        self._value_reader = value_reader or widget_value

    def register(self, key, label, widget, section=''):
        label_widget = None
        parent = widget.parentWidget()
        if parent and isinstance(parent.layout(), QFormLayout):
            label_widget = parent.layout().labelForField(widget)
            if isinstance(label_widget, QLabel) and not label_widget.text().rstrip().endswith('*'):
                label_widget.setText(label_widget.text().rstrip() + ' <span style="color:#D85858">*</span>')
        self._fields[key] = {'key': key, 'label': label, 'widget': widget, 'section': section, 'label_widget': label_widget, 'base_label': label_widget.text() if isinstance(label_widget,QLabel) else ''}
        widget.setProperty('validation_key', key)
        widget.setToolTip(widget.toolTip() or 'Required field')
        signal = None
        if isinstance(widget, QLineEdit): signal = widget.textChanged
        elif isinstance(widget, QTextEdit): signal = widget.textChanged
        elif isinstance(widget, QComboBox): signal = widget.currentTextChanged
        elif isinstance(widget, QDateEdit): signal = widget.dateChanged
        if signal is not None:
            signal.connect(self.validate)

    def fields(self):
        return list(self._fields.values())

    def is_valid(self, field):
        return bool(self._value_reader(field['widget']))

    def validate(self, *_args):
        missing = []
        section_totals = {}
        section_complete = {}
        completed = 0
        for field in self._fields.values():
            ok = self.is_valid(field)
            field['widget'].setStyleSheet(VALID_STYLE if ok else INVALID_STYLE)
            field['widget'].setProperty('validation_valid', ok)
            lw = field.get('label_widget')
            if isinstance(lw, QLabel):
                base = field.get('base_label','')
                lw.setText(base + (' <span style="color:#2E8B57">✓</span>' if ok else ''))
            section = field['section']
            section_totals[section] = section_totals.get(section, 0) + 1
            section_complete[section] = section_complete.get(section, 0) + int(ok)
            if ok:
                completed += 1
            else:
                missing.append(field)
        total = len(self._fields)
        result = {
            'total': total,
            'completed': completed,
            'percent': round(completed / max(1, total) * 100),
            'missing': missing,
            'section_totals': section_totals,
            'section_complete': section_complete,
        }
        if self.changed:
            self.changed.emit(result)
        return result

    def focus_field(self, key):
        field = self._fields.get(key)
        if not field:
            return False
        widget = field['widget']
        widget.setFocus()
        if hasattr(widget, 'selectAll'):
            try: widget.selectAll()
            except Exception: pass
        previous = widget.styleSheet()
        widget.setStyleSheet(FOCUS_STYLE)
        QTimer.singleShot(1400, lambda w=widget, p=previous: w.setStyleSheet(p))
        return True
