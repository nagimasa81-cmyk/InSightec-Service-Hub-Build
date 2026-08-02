from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")

load_start = source.index("    def load_template")
load_end = source.index("    def _make_pane", load_start)
load_source = source[load_start:load_end]

assert load_source.count("_progress_checkpoint(") >= 7
assert "record_index % batch_size == 0" in load_source
assert "row_index % 1000 == 0" in load_source
assert "row_index % 2000 == 0" in load_source
assert "setUpdatesEnabled(False)" in load_source

print("Commit0028 cancellation checkpoints: PASS")
