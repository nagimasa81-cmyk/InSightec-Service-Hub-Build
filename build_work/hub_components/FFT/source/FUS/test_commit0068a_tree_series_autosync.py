from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
CONTROLLER = (ROOT / "navigation_controller.py").read_text(encoding="utf-8")


def test_series_is_expanded_before_image_load():
    expansion = CONTROLLER.index("self.tree_sync.change_series(")
    image_load = CONTROLLER.index("w.show_dicom(result.current_item)", expansion)
    assert expansion < image_load


def test_series_sync_collapses_others_and_selects_target():
    method = APP[APP.index("def _set_tree_series_expansion_for_index"):]
    assert ("item.setExpanded(item is target_series)" in method or "sibling.setExpanded(sibling is target_series)" in method)
    assert "parent.setExpanded(True)" in method
    assert "self.tree.setCurrentItem(target_item)" in method
    assert "self.tree.scrollToItem(target_item)" in method
    assert "return True" in method
