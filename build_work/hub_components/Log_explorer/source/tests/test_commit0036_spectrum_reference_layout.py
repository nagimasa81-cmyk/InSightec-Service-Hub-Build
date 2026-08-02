from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "foundation" / "spectrum_analysis.py"
).read_text(encoding="utf-8")

for token in [
    'self.energy_plot.mode = "Energy per Band"',
    'self.plot.mode = "Raw Data from A2D"',
    'self.frequency_plot.mode = "Spectrum"',
    'QLabel("Measure #")',
    'QLabel("Save Spectrum Data:")',
    'QLabel("Channels:")',
    'QLabel("Bands:")',
    '"Packet Validity"',
    '"Sonic State"',
    '"Band Energy"',
    "def _measure_changed",
    "def _update_packet_table",
]:
    assert token in source, token

print("Commit0036 Spectrum reference layout: PASS")
