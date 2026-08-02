from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

# Static source verification. Runtime GUI import is covered by EXE test.
source = (root / "foundation" / "spectrum_analysis.py").read_text(encoding="utf-8")
for needle in [
    "def parse_spectrum_dump",
    "gzip.decompress",
    "acoustic_power",
    "main_frequency_hz",
    "class SpectrumAnalysisWidget",
    "Spectrum_*.dmp_FFT",
]:
    assert needle in source, needle

print("Spectrum module static test: PASS")
