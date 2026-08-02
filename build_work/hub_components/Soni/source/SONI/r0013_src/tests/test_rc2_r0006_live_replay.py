from pathlib import Path


def _source():
    return (Path(__file__).parents[1] / "src/ui/main_window.py").read_text(encoding="utf-8")


def test_planning_strip_rebuild_does_not_auto_display_ct():
    source = _source()
    forbidden = 'self._unified_image_selected(strip, middle)'
    assert forbidden not in source


def test_navigation_restores_live_replay_mode():
    source = _source()
    assert 'def _activate_replay_mode_for_navigation' in source
    assert '{"planning", "planning_ct", "planning_mr"}' in source
    assert '"thermal" if self.current and self.current.temperature_frames else "anatomy"' in source


def test_all_navigation_paths_activate_replay():
    source = _source()
    for signature in ('def slider_changed', 'def previous_frame', 'def next_frame', 'def wheelEvent'):
        block = source[source.index(signature):]
        block = block[:block.find('\n    def ', 5) if '\n    def ' in block[5:] else len(block)]
        assert '_activate_replay_mode_for_navigation()' in block
