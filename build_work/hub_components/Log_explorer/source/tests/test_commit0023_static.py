from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
spectrum = (root / "foundation" / "spectrum_analysis.py").read_text(encoding="utf-8")

entry = main.rfind('if __name__ == "__main__":')
for needle in [
    'APP_VERSION = "2.0.0-rc1-commit0023"',
    "Quick Filter:",
    "CSA recovery parser",
    "MultiPaneLogViewer.apply_view_filters = _c23_apply_view_filters",
    "MultiPaneLogViewer.load_pane = _c23_load_pane",
    "Spectrum Dumps are Investigation assets only",
]:
    assert 0 <= main.find(needle) < entry, needle

for needle in [
    '"Waterfall"',
    '"Heatmap"',
    '"Harmonics"',
    '"FFT Compare"',
    '"Sonication Replay"',
    "def _replay_tick",
]:
    assert needle in spectrum, needle

print("Commit0023 static integration: PASS")
