from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_WINDOW = ROOT / "src" / "ui" / "main_window.py"


def _main_window_class() -> ast.ClassDef:
    tree = ast.parse(MAIN_WINDOW.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")


def test_main_window_has_no_missing_private_method_references() -> None:
    cls = _main_window_class()
    methods = {
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assigned: set[str] = set()
    references: list[tuple[str, int]] = []
    for node in ast.walk(cls):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    assigned.add(target.attr)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                assigned.add(target.attr)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        ):
            references.append((node.attr, getattr(node, "lineno", 0)))

    missing = sorted(
        {
            name
            for name, _line in references
            if name.startswith("_") and name not in methods and name not in assigned
        }
    )
    assert missing == []


def test_removed_rc2_callback_is_not_registered() -> None:
    source = MAIN_WINDOW.read_text(encoding="utf-8")
    assert 'register("atomic_frame_snapshot", self._render_replay_selection)' not in source
    assert "def _render_replay_selection" not in source


def test_time_mapping_helpers_exist() -> None:
    methods = {
        node.name
        for node in _main_window_class().body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_replay_duration_s" in methods
    assert "_seconds_to_index" in methods
    assert "_index_to_seconds" in methods
