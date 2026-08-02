from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
NAV = Path('navigation_controller.py').read_text(encoding='utf-8')
TOOLBAR = Path('viewer_toolbar.py').read_text(encoding='utf-8')


def test_modules_created_and_imported():
    assert 'class NavigationController' in NAV
    assert 'class ViewerToolbar' in TOOLBAR
    assert 'from navigation_controller import NavigationController' in APP
    assert 'from viewer_toolbar import ViewerToolbar' in APP


def test_toolbar_routes_previous_next_to_continuous_navigation():
    assert 'previousRequested.connect' in APP
    assert 'change_slice_continuous(-1)' in APP
    assert 'nextRequested.connect' in APP
    assert 'change_slice_continuous(1)' in APP


def test_existing_widget_attribute_contract_is_preserved():
    for name in ('btn_fft', 'btn_original', 'btn_both', 'prev_btn', 'next_btn', 'slice_label'):
        assert f'self.{name} =' in APP


def test_controller_crosses_series_and_preserves_display_mode():
    # Commit0067-3 delegates series-boundary calculation to the provider.
    assert 'DicomNavigationProvider' in NAV
    assert 'provider.previous() if step < 0 else provider.next()' in NAV
    assert 'mode = getattr(w, "view_mode", "Both")' in NAV
    assert 'if result.series_changed:' in NAV
    assert 'self.tree_sync.change_series(' in NAV


def test_version_marker():
    assert 'Commit0067-2' in APP or 'Commit0067-3' in APP
