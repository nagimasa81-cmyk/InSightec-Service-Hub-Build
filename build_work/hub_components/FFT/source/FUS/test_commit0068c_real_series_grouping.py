from pathlib import Path

APP = (Path(__file__).resolve().parent / 'app.py').read_text(encoding='utf-8')


def test_navigation_series_key_matches_tree_boundary():
    method = APP[APP.index('def _entry_navigation_series_key'):APP.index('def _current_series_indices')]
    assert 'SeriesInstanceUID' in method
    assert 'AcquisitionNumber' not in method
    assert 'EchoNumbers' not in method
    assert 'TemporalPositionIdentifier' not in method


def test_ordered_groups_are_restricted_to_current_study():
    method = APP[APP.index('def _ordered_series_groups'):APP.index('def _set_tree_series_expansion_for_index')]
    assert 'current_study' in method
    assert 'if self._entry_study_key(entry) != current_study' in method
    assert 'groups.sort' in method


def test_boundary_navigation_clears_hiding_series_filter():
    method = APP[APP.index('def _set_tree_series_expansion_for_index'):APP.index('def _navigate_tree_source_continuous')]
    assert 'setCurrentText("All Series")' in method
    assert 'self._apply_explorer_filters()' in method
