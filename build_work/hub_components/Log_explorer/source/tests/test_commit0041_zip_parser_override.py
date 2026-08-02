from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

for token in [
    "def _c41_parse_selected_zip_files_to_memory",
    "_parse_selected_zip_files_to_memory = _c41_parse_selected_zip_files_to_memory",
    "def _c41_parse_zip_file",
    '"gesys-section"',
    '"review-canonical"',
    '"psc-dedicated"',
]:
    assert token in source, token

entry = source.rfind('if __name__ == "__main__":')
assignment = source.rfind(
    "_parse_selected_zip_files_to_memory = "
    "_c41_parse_selected_zip_files_to_memory"
)
assert assignment < entry

print("Commit0041 ZIP parser override: PASS")
