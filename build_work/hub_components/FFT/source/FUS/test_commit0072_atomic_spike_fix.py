from pathlib import Path

SOURCE = Path(__file__).with_name('app.py').read_text(encoding='utf-8')

def test_atomic_image_replacement():
    assert 'view.disableAutoRange()' in SOURCE
    assert 'self.plot.viewport().setUpdatesEnabled(False)' in SOURCE
    assert 'update=False' in SOURCE

def test_spike_validation_uses_predicted_direction():
    assert 'projection_strength' in SOURCE
    assert 'strong_line' in SOURCE
    assert 'minimum_energy = 0.0015' in SOURCE

def test_geometry_does_not_autorange_after_selection():
    block = SOURCE[SOURCE.index('def _apply_default_image_geometry'):SOURCE.index('def _render_current_image_atomically')]
    assert 'autoRange' not in block
    assert 'disableAutoRange' in block
