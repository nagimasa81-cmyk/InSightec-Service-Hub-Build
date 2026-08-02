from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
path = root / "foundation" / "investigation.py"
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

workspace = next(
    node
    for node in tree.body
    if isinstance(node, ast.ClassDef)
    and node.name == "InvestigationWorkspace"
)
segment = "\n".join(
    source.splitlines()[workspace.lineno - 1:workspace.end_lineno]
)

# No automatic analysis during construction.
init_method = next(
    node for node in workspace.body
    if isinstance(node, ast.FunctionDef) and node.name == "__init__"
)
init_source = "\n".join(
    source.splitlines()[init_method.lineno - 1:init_method.end_lineno]
)
assert "self.load_template()" not in init_source
assert "self._show_ready_state()" in init_source

for token in [
    "Start Analysis",
    "No records are processed when Investigation Mode is opened",
    "max_visible_rows_per_source",
    "_progress_checkpoint",
    "_select_visible_records",
    "_populate_visible_tables",
    "_rebuild_timeline_only",
    "progress.wasCanceled()",
]:
    assert token in segment, token

print("Commit0028 Investigation performance/static flow: PASS")
