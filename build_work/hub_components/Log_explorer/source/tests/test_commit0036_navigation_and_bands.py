from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "foundation" / "spectrum_analysis.py"
).read_text(encoding="utf-8")

for token in [
    'QPushButton("|<")',
    'QPushButton("<")',
    'QPushButton(">")',
    'QPushButton(">|")',
    "self.measure_spin.setMaximum",
    "self.file_list.setCurrentRow(index)",
    "self.energy_plot.selected_bands",
    "for band_index in range(6)",
]:
    assert token in source, token

print("Commit0036 navigation and bands: PASS")
