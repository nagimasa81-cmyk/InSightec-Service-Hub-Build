from pathlib import Path

APP = Path(__file__).with_name('app.py').read_text(encoding='utf-8')

def test_active_panel_drives_auto_level():
    assert 'def _set_active_image_panel' in APP
    assert 'target = "Raw Data" if role == "fft" else "Original Image"' in APP
    assert 'self._set_levels_for_target(target, array)' in APP

def test_fft_initial_level_signature_reset():
    assert '_fft_level_signature' in APP
    assert 'self.raw_window_level = None' in APP
    assert 'self.raw_dynamic_range = None' in APP

def test_right_menu_defaults_collapsed():
    assert 'AccordionSection("Image Tools",image_tools_content,False)' in APP
    assert 'AccordionSection("Dynamic Range / Window Level",display_group,False)' in APP
    assert 'AccordionSection("Spike",spike_content,False)' in APP

def test_crosshair_profiles_are_horizontal_and_vertical():
    assert 'Horizontal Crosshair Profile' in APP
    assert 'Vertical Crosshair Profile' in APP
    assert 'horizontal = np.asarray(arr[row, :], dtype=float)' in APP
    assert 'vertical = np.asarray(arr[:, col], dtype=float)' in APP
