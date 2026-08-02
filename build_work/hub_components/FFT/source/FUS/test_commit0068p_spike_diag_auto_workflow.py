from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_spike_tab_activation_is_connected():
    assert "self.tabs.currentChanged.connect(self._main_tab_changed)" in SOURCE
    assert "if index == 1:" in SOURCE
    assert "self._activate_spike_diag_from_workspace_selection" in SOURCE


def test_series_selection_expands_to_dicom_leaves_in_tree_order():
    assert "selected_image_or_series_ancestor" in SOURCE
    assert 'data[0] in ("dicom", "series")' in SOURCE
    assert "QTreeWidgetItemIterator preserves the Explorer's top-to-bottom order" in SOURCE


def test_auto_processing_keeps_all_analyzed_images():
    method = SOURCE.split("def _activate_spike_diag_from_workspace_selection", 1)[1].split("def apply_spike_processing", 1)[0]
    assert 'results.append({' in method
    assert '"detected": detected' in method
    assert "if candidates" not in method.split("results.append", 1)[0]


def test_first_processed_image_is_displayed_by_default():
    assert "index = 0 if select_first else len(results) - 1" in SOURCE
    assert "self._refresh_spike_diag(select_first=True)" in SOURCE


def test_processed_list_selection_updates_result_panels():
    assert "self.spike_result_list.itemClicked.connect(self._spike_result_selected)" in SOURCE
    assert "self._show_spike_result(int(index))" in SOURCE
