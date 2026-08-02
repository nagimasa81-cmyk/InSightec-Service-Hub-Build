from pathlib import Path

APP = Path(__file__).with_name('app.py').read_text(encoding='utf-8')


def test_original_is_left_and_fft_is_right():
    assert 'self.primary_panel = ImagePanel("Original")' in APP
    assert 'self.secondary_panel = ImagePanel("FFT (k-space)")' in APP
    assert 'return "original" if panel is self.primary_panel else "fft"' in APP


def test_four_equal_independent_profile_plots_exist():
    for name in (
        'original_horizontal_profile', 'original_vertical_profile',
        'fft_horizontal_profile', 'fft_vertical_profile',
    ):
        assert name in APP
    assert 'original_profiles_layout.addWidget(self.original_horizontal_profile, 1)' in APP
    assert 'original_profiles_layout.addWidget(self.original_vertical_profile, 1)' in APP
    assert 'fft_profiles_layout.addWidget(self.fft_horizontal_profile, 1)' in APP
    assert 'fft_profiles_layout.addWidget(self.fft_vertical_profile, 1)' in APP


def test_crosshairs_are_independent():
    assert 'self.panel_crosshairs' in APP
    assert 'def _panel_crosshair_position' in APP
    assert 'lambda row, col: self._line_moved(self.primary_panel, row, col)' in APP
    assert 'lambda row, col: self._line_moved(self.secondary_panel, row, col)' in APP


def test_raw_load_does_not_force_both_or_double_paint():
    assert 'two-stage paint briefly showed Original and then forced Both' in APP
    assert 'QTimer.singleShot(80, finish_both_display)' not in APP
    assert 'self.view_mode = "Both"\n            self.btn_original.setChecked(False)' not in APP


def test_arrow_navigation_has_raw_tree_fallback():
    assert 'def _navigate_tree_source_continuous' in APP
    assert 'if self.source_kind != "dicom" or not self.dicom_entries:' in APP
    assert 'old_parent.setExpanded(False)' in APP
    assert 'parent.setExpanded(True)' in APP
