from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
CONTROLLER = (ROOT / "navigation_controller.py").read_text(encoding="utf-8")

def test_destination_is_resolved_after_filter_rebuild():
    method = APP[APP.index("def _set_tree_series_expansion_for_index"):APP.index("def _navigate_tree_source_continuous")]
    assert method.index("self._apply_explorer_filters()") < method.index("target_item = self._find_tree_dicom_item(index)")

def test_series_is_reexpanded_after_show_dicom():
    method = CONTROLLER[CONTROLLER.index("def navigate_continuous"):CONTROLLER.index("def update_ui")]
    assert "w.show_dicom(result.current_item)" in method
    assert "expansion_handler(result.current_item)" in method
    assert "QTimer.singleShot(0" in method

def test_tree_selection_preserves_parent_expansion():
    method = APP[APP.index("def _select_tree_dicom_index"):APP.index("def _level_target_changed")]
    assert "ancestor.setExpanded(True)" in method
    assert "self.tree.scrollToItem(item)" in method

def test_version_identifies_commit0068g():
    assert "Commit0068i" in APP
