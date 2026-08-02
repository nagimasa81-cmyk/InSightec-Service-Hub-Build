from pathlib import Path
import json


def test_version_commit0060a():
    data = json.loads(Path("version.json").read_text(encoding="utf-8"))
    assert data["version"] == "5.10.1"
    assert data["commit"] == "Commit0060a_Orientation_Button_AP_Series_Navigation_Hotfix"


def test_orientation_dialog_default_dataset_argument():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "def _dicom_orientation_labels(self, ds=None):" in text
    assert "dataset = ds if ds is not None else self.current_ds" in text


def test_ge_console_orientation_not_double_flipped():
    app_text = Path("app.py").read_text(encoding="utf-8")
    engine_text = Path("orientation_engine.py").read_text(encoding="utf-8")
    assert '"y_axis_up": False' in app_text
    assert "y_axis_up: bool = False" in engine_text
    assert 'value.get("y_axis_up", False)' in engine_text


def test_previous_next_are_locked_to_current_series():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "def _current_series_indices(self):" in text
    assert "Navigate only inside the currently displayed DICOM series." in text
    assert "target_index = indices[target_position]" in text
    assert "self._update_series_navigation_ui()" in text
