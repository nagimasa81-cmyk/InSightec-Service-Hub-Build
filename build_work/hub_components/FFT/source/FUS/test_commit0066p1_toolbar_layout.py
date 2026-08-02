from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_toolbar_has_verification_object_name():
    assert 'setObjectName("ViewerTopDisplayNavigationToolbar")' in SOURCE


def test_toolbar_is_not_inserted_in_center_column():
    assert 'cl.addWidget(self.mode_toolbar_widget)' not in SOURCE


def test_toolbar_spans_viewer_workspace():
    assert 'viewer_workspace_layout.addWidget(self.mode_toolbar_widget)' in SOURCE
    assert 'self.viewer_content_splitter.addWidget(center)' in SOURCE
    assert 'self.viewer_content_splitter.addWidget(right_scroll)' in SOURCE


def test_outer_splitter_is_explorer_and_viewer_only():
    assert 'main_split.addWidget(self.viewer_workspace)' in SOURCE
    assert 'main_split.setSizes([210, 1140])' in SOURCE


def test_version_marker():
    assert 'Commit0066P1' in SOURCE
