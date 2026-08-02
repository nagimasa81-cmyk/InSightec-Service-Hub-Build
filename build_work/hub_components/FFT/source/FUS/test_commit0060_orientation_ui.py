from pathlib import Path


def test_commit0060_version():
    import json
    data = json.loads(Path('version.json').read_text(encoding='utf-8'))
    assert data['version'] in ('5.10.0', '5.10.1')
    assert data['commit'] in ('Commit0060_Orientation_UI_GE_Display', 'Commit0060a_Orientation_Button_AP_Series_Navigation_Hotfix')


def test_ge_console_presets_present():
    text = Path('app.py').read_text(encoding='utf-8')
    assert '"Axial": {"top": "A", "bottom": "P", "left": "L", "right": "R"}' in text
    assert '"Coronal": {"top": "S", "bottom": "I", "left": "L", "right": "R"}' in text
    assert '"Sagittal": {"top": "S", "bottom": "I", "left": "P", "right": "A"}' in text


def test_orientation_button_uses_reliable_wrapper():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'self._open_orientation_dialog' in text
    assert 'dialog.raise_()' in text
    assert 'dialog.activateWindow()' in text
