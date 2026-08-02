"""Compatibility guard superseded by Commit0080.

Commit0079 used runtime import anchors. Commit0080 intentionally removes them
and keeps decoder packaging entirely in the build configuration.
"""
from pathlib import Path


def test_commit0080_supersedes_runtime_plugin_anchor():
    assert not Path("pydicom_nuitka_plugins.py").exists()
    launcher = Path("launcher.py").read_text(encoding="utf-8")
    assert "register_packaged_plugins" not in launcher
