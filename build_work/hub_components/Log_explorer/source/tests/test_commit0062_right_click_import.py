from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "LogMergeTool_NoExcel_Main.py"
text = SOURCE.read_text(encoding="utf-8")
tree = ast.parse(text)

imports = {
    alias.name
    for node in tree.body
    if isinstance(node, ast.Import)
    for alias in node.names
}
assert "unicodedata" in imports, "unicodedata must be imported at module scope"

namespace = {}
start = text.index("def _c60_normalize")
end = text.index("\ndef _c60_resolve_column", start)
exec("import re\nimport unicodedata\n" + text[start:end], namespace)
assert namespace["_c60_normalize"](" Ｅrror  35 ") == "error 35"
print("Commit0062 right-click import regression: PASS")
