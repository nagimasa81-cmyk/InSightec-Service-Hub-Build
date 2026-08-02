from pathlib import Path


def test_controller_limits_explorer_items_to_active_kind():
    text = Path('navigation_controller.py').read_text(encoding='utf-8')
    assert 'def _active_explorer_kind' in text
    assert 'data[0] == expected_kind' in text
    assert 'current_source' in text


def test_tree_sync_collapses_actual_current_parent():
    text = Path('core/tree_sync.py').read_text(encoding='utf-8')
    assert 'current_item = self.tree.currentItem()' in text
    assert 'previous_parent = current_parent or self._last_parent' in text
