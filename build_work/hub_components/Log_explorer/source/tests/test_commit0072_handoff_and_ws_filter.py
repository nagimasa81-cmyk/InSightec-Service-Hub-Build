from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "LogMergeTool_NoExcel_Main.py"
TEXT = SRC.read_text(encoding="utf-8")

def test_handoff_is_capped_at_two_panes():
    assert "types = preferred[:2]" in TEXT
    assert "visible_count = min(2, len(types)" in TEXT

def test_ws_filter_is_exact_and_ws_only():
    assert 'level in {"err", "error"} and "code" in message and "true" in message' in TEXT
    assert "button.setVisible(is_ws)" in TEXT
    assert 'modes[pane_index] = "ALL"' in TEXT
