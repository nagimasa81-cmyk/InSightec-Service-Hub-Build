from pathlib import Path


def test_no_direct_gdcm_import():
    source = Path("app.py").read_text(encoding="utf-8")
    manager = Path("decoder_manager.py").read_text(encoding="utf-8")
    assert "pydicom.pixels.decoders.gdcm" not in source + manager
    assert "decode_dicom_pixels(ds)" in source


def test_nuitka_packages_complete():
    build = Path("03_BUILD_NUITKA_STANDALONE.bat").read_text(encoding="utf-8")
    assert "--include-package=pydicom" in build
    assert "--include-package=pylibjpeg" in build


def test_version_updated():
    version_text = Path("version.json").read_text(encoding="utf-8")
    assert any(commit in version_text for commit in ("Commit0080", "Commit0081", "Commit0082"))
