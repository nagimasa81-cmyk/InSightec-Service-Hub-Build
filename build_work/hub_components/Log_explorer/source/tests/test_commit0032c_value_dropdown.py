from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    "def _c32c_column_unique_values",
    "def _c32c_apply_selected_value",
    "def _c32c_show_header_context_menu",
    'value_menu = menu.addMenu("Select value")',
    "if 1 <= len(values) <= 10:",
    "_c30_show_header_context_menu = _c32c_show_header_context_menu",
]:
    assert token in source, token

entry = source.rfind('if __name__ == "__main__":')
assert source.index("def _c32c_column_unique_values") < entry

print("Commit0032C header value dropdown integration: PASS")
