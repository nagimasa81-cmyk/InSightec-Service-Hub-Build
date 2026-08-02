from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
path = root / "foundation" / "investigation.py"
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

classes = {
    node.name: node
    for node in tree.body
    if isinstance(node, ast.ClassDef)
}

assert "AcquisitionDashboard" in classes
assert "InvestigationWorkspace" in classes

def class_source(name):
    node = classes[name]
    return "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno])

acquisition = class_source("AcquisitionDashboard")
workspace = class_source("InvestigationWorkspace")

# The dashboard must not own Investigation Viewer controls.
assert "viewer_count_combo" not in acquisition
assert "_change_viewer_count" not in acquisition
assert "_equalize_viewer_widths" not in acquisition

# The real Investigation workspace owns and connects them.
for token in [
    "self.viewer_control_bar",
    "self.viewer_count_combo",
    "self._change_viewer_count",
    "self.equal_widths_button",
    "self._equalize_viewer_widths",
    "investigation_root.addWidget(self.viewer_control_bar)",
]:
    assert token in workspace, token

print("Commit0027 Investigation control ownership: PASS")
