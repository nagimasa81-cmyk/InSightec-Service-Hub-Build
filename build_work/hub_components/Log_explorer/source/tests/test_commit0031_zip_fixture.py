from pathlib import Path
import tempfile
import zipfile

with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    name = "Spectrum_Thu_Jul_02_11_09_28_2026.dmp_FFT"
    package = temp / "site.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(f"deep/a/b/c/{name}", b"sample")
    with zipfile.ZipFile(package, "r") as archive:
        assert any(Path(item).name == name for item in archive.namelist())

print("Commit0031 ZIP fixture: PASS")
