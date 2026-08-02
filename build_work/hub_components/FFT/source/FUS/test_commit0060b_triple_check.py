from pathlib import Path
import json


def test_version_commit0060b():
    data = json.loads(Path('version.json').read_text(encoding='utf-8'))
    assert data['version'] == '5.10.2'
    assert data['commit'] == 'Commit0060b_Orientation_Triple_Check_Hotfix'


def test_only_one_orientation_label_method_exists():
    text = Path('app.py').read_text(encoding='utf-8')
    assert text.count('def _dicom_orientation_labels(self, ds=None):') == 1


def test_ge_jis_plane_presets():
    text = Path('app.py').read_text(encoding='utf-8')
    assert '"Axial": {"top": "A", "bottom": "P", "left": "L", "right": "R"}' in text
    assert '"Coronal": {"top": "S", "bottom": "I", "left": "L", "right": "R"}' in text
    assert '"Sagittal": {"top": "S", "bottom": "I", "left": "P", "right": "A"}' in text
    assert 'labels.update(self._effective_orientation_labels())' in text


def test_orientation_dialog_is_safe_without_image():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'Load an image before changing orientation.' in text
    assert 'selected_plane = plane_combo.currentText()' in text


def test_navigation_is_series_locked():
    text = Path('app.py').read_text(encoding='utf-8')
    assert 'def _current_series_indices(self):' in text
    assert 'target_index = indices[target_position]' in text
    assert 'Navigate only inside the currently displayed DICOM series.' in text
    assert '|{protocol}|{sequence}' in text
