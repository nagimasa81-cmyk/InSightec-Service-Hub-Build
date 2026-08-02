from pathlib import Path

root = Path(__file__).resolve().parents[1]
spectrum = (
    root / "foundation" / "spectrum_analysis.py"
).read_text(encoding="utf-8")
console = (
    root / "foundation" / "sonication_console.py"
).read_text(encoding="utf-8")

for token in [
    "mouseDoubleClickEvent",
    "QRectF(plot).contains(self.crosshair_pos)",
    "Cavitation candidate",
    "Reset Zoom",
]:
    assert token.lower() in spectrum.lower(), token

for token in [
    "Sonication Replay",
    "Stable Cavitation",
    "Inertial Cavitation",
    "Broadband",
]:
    assert token in console, token

print("Commit0036 retained features: PASS")
