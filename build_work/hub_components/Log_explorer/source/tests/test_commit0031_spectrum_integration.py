from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
spectrum = (root / "foundation" / "spectrum_analysis.py").read_text(encoding="utf-8")
investigation = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")

for token in [
    'APP_VERSION = "2.0.0-rc1-commit0031"',
    "Spectrum Analysis — Standalone",
    "Select Files",
    "Select Folder",
    "Select ZIP",
]:
    assert token in main, token

for token in [
    "def _extract_spectrum_members_from_zip",
    "def find_spectrum_dumps",
    "zip_members_scanned",
    "def source_paths",
    "def use_loaded_sources",
]:
    assert token in spectrum, token

for token in [
    "Spectrum save events",
    "Sonication state",
    "self.acquisition_dashboard.set_records",
    "self.spectrum_analysis.use_loaded_sources",
]:
    assert token in investigation, token

print("Commit0031 Spectrum/Acquisition integration: PASS")
