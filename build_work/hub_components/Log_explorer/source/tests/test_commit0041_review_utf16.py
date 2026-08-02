from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

start = source.index("def _c41_decode_review_text")
end = source.index("def _c41_review_lines", start)
segment = source[start:end]

for token in [
    '"utf-16"',
    '"utf-16-le"',
    '"utf-16-be"',
    "raw.count(b\"\\x00\")",
]:
    assert token in segment, token

assert segment.index('"utf-16"') < segment.index(
    'raw.replace(b"\\x00", b"\\n")'
)

print("Commit0041 Review UTF-16 decoding order: PASS")
