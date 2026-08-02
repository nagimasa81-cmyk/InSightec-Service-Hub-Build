from pathlib import Path
root = Path(__file__).resolve().parents[1]
console = (root/"foundation"/"sonication_console.py").read_text(encoding="utf-8")
for feature in [
    "Replay", "Acquisition", "Spectrum", "VIMeasure", "Temperature",
    "Stable Cavitation", "Inertial Cavitation", "Broadband",
    "Hydrophone", "Correlation",
]:
    assert feature.lower() in console.lower(), feature
print("Commit0035 requested feature contract: PASS")
