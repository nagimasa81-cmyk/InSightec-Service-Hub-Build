from pathlib import Path
root=Path(__file__).resolve().parents[1]
sp=(root/"foundation"/"spectrum_analysis.py").read_text(encoding="utf-8")
iv=(root/"foundation"/"investigation.py").read_text(encoding="utf-8")
for token in [
 "Raw / Reconstructed Data", 'QPushButton("All")', 'QPushButton("None")',
 "Crosshair", "mouseDoubleClickEvent", "Reset Zoom", "Cavitation candidate",
]:
 assert token.lower() in sp.lower(), token
for token in ["sonication_table","_populate_sonication_table","Sonication Investigation Prototype"]:
 assert token in iv, token
print("Commit0033 rich Spectrum/Acquisition UI: PASS")
