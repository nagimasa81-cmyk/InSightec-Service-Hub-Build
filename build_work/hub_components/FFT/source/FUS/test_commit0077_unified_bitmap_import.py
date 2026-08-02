import ast
import json
from pathlib import Path


def _app_source_and_tree():
    source = Path("app.py").read_text(encoding="utf-8")
    return source, ast.parse(source)


def test_bitmap_extensions_are_complete_and_shared():
    source, tree = _app_source_and_tree()
    values = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "BITMAP_EXTENSIONS" for t in node.targets):
                call = node.value
                assert isinstance(call, ast.Call)
                values = ast.literal_eval(call.args[0])
                break
    assert values is not None
    assert {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"} <= set(values)
    assert source.count("suffix in BITMAP_EXTENSIONS") >= 2
    assert "path.suffix.lower() in BITMAP_EXTENSIONS" in source


def test_build_metadata_matches_entry_point():
    metadata = json.loads(Path("version.json").read_text(encoding="utf-8"))
    assert metadata["commit"] in {"Commit0077", "Commit0078", "Commit0079", "Commit0080"}
    assert metadata["entry_point"] in {"app.py", "launcher.py"}
    assert Path(metadata["entry_point"]).is_file()
    assert metadata["exe_name"].lower().endswith(".exe")
