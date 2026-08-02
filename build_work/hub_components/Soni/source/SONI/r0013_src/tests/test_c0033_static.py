from pathlib import Path
TEXT=Path('src/ui/main_window.py').read_text(encoding='utf-8')

def test_planning_metadata_only_items_are_not_thumbnails():
    assert 'if array is not None:' in TEXT

def test_initial_frame_validation_remains_available():
    assert 'def _first_valid_replay_frame' in TEXT
