from pathlib import Path

APP = Path(__file__).with_name('app.py').read_text(encoding='utf-8')


def test_slice_navigation_is_series_local():
    assert 'def _current_series_indices(self):' in APP
    assert 'target_index = indices[target_position]' in APP
    assert 'SeriesDescription' in APP and 'AcquisitionNumber' in APP


def test_show_dicom_preserves_view_mode():
    block = APP[APP.index('def show_dicom'):APP.index('def dicom_info')]
    assert 'self.view_mode = "Both"' not in block
    assert 'Preserve the user\'s current Single/FFT/Both layout' in block


def test_standard_mouse_mapping():
    assert 'left-drag = pan' in APP
    assert 'right-drag = window level / width' in APP
    assert 'wheel = slice paging; Ctrl+wheel = zoom' in APP
    assert 'self.pageRequested.emit(1 if event.angleDelta().y() < 0 else -1)' in APP


def test_mouse_mode_items_removed_from_context_menu():
    block = APP[APP.index('def _show_mouse_action_menu'):APP.index('def wheelEvent', APP.index('def _show_mouse_action_menu'))]
    for removed in ('Window / Level mode', 'Pan mode', 'Zoom rectangle mode', 'Mouse wheel paging'):
        assert removed not in block


def test_pixels_and_labels_share_transform():
    assert 'def _resolve_console_display_transform' in APP
    assert 'def _apply_display_transform_to_array' in APP
    assert 'self.console_display_transform = self._resolve_console_display_transform' in APP
    assert 'labels = self._sync_labels_to_original_display(base_labels, transform)' in APP
