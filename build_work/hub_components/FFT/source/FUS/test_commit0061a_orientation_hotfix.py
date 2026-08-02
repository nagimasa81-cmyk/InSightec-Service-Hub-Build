from pathlib import Path

APP = Path(__file__).with_name('app.py').read_text(encoding='utf-8')


def test_orientation_geometry_is_untransformed_before_display_sync():
    block = APP[APP.index('def _dicom_orientation_labels'):APP.index('def _apply_orientation_transform_to_labels')]
    assert 'engine.base_labels(geometry)' in block
    assert 'engine.calculate(dataset, self._current_original_display_transform())' not in block


def test_none_override_cannot_render_as_none_text():
    block = APP[APP.index('def _apply_image_orientation'):APP.index('def _transform_current_image')]
    assert 'overrides.get(edge) is not None' in block
    assert 'Never convert' in block


def test_orientation_transform_buttons_keep_dialog_open():
    block = APP[APP.index('def edit_image_orientation'):APP.index('def _annotation_lines')]
    assert 'dialog.accept()' not in block
    assert 'apply_labels_live' in block
    assert 'dialog.raise_()' in block
    assert 'dialog.activateWindow()' in block

def test_medical_raster_row_zero_is_displayed_at_top():
    assert 'self.plot.getViewBox().invertY(True)' in APP
