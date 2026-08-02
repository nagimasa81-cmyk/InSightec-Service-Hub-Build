from pathlib import Path
root = Path(__file__).resolve().parents[1]
console = (root/"foundation"/"sonication_console.py").read_text(encoding="utf-8")
investigation = (root/"foundation"/"investigation.py").read_text(encoding="utf-8")
for token in [
    "class SonicationReplayConsole",
    "Build Synchronized Timeline",
    "Cross-source Correlation",
    "Hydrophone / Cavitation",
    "_nearest_correlation",
    "_band_energy",
    "_broadband_score",
]:
    assert token in console, token
for token in [
    "from foundation.sonication_console import SonicationReplayConsole",
    'self.analysis_tabs.addTab(',
    '"Sonication Replay"',
    "self.sonication_console.timeChanged.connect(self.sync_all_to_time)",
]:
    assert token in investigation, token
print("Commit0035 Sonication console integration: PASS")
