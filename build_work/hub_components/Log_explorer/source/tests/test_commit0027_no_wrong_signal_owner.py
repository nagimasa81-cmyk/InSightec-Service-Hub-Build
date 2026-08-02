from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
source = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")
tree = ast.parse(source)

for node in tree.body:
    if not isinstance(node, ast.ClassDef):
        continue

    segment = "\n".join(
        source.splitlines()[node.lineno - 1:node.end_lineno]
    )

    if "currentTextChanged.connect(" in segment and "_change_viewer_count" in segment:
        method_names = {
            child.name
            for child in node.body
            if isinstance(child, ast.FunctionDef)
        }
        assert "_change_viewer_count" in method_names, node.name
        assert "_equalize_viewer_widths" in method_names, node.name

print("Commit0027 signal-owner validation: PASS")
