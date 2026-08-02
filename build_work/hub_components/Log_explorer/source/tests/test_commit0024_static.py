from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
spectrum = (root / "foundation" / "spectrum_analysis.py").read_text(encoding="utf-8")
investigation = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")

entry = main.rfind('if __name__ == "__main__":')
for token in [
    'APP_VERSION = "2.0.0-rc1-commit0024"',
    "class StandaloneSpectrumWindow",
    "Spectrum Analysis",
    "setAcceptDrops(True)",
]:
    assert 0 <= main.find(token) < entry, token

for token in [
    "def is_spectrum_dump",
    "def find_spectrum_dumps",
    "path.rglob",
    "def dragEnterEvent",
    "def dropEvent",
]:
    assert token in spectrum, token

for token in [
    "class AcquisitionDashboard",
    "class AcquisitionChart",
    "viewer_count_combo",
    "_change_viewer_count",
    "_equalize_viewer_widths",
]:
    assert token in investigation, token

print("Commit0024 static integration: PASS")
