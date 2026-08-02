from pathlib import Path


def test_launcher_has_no_decoder_preload():
    source = Path("launcher.py").read_text(encoding="utf-8")
    assert "register_packaged_plugins" not in source
    assert "pydicom_nuitka_plugins" not in source


def test_decoder_is_lazy_and_gdcm_free():
    source = Path("decoder_manager.py").read_text(encoding="utf-8")
    assert "def decode_dicom_pixels" in source
    assert "_select_decoder" in source
    assert "decoding_plugin=plugin" in source
    assert "pydicom.pixels.decoders.gdcm" not in source
    assert "import gdcm" not in source


def test_nuitka_build_uses_package_inclusion_not_runtime_anchors():
    source = Path("03_BUILD_NUITKA_STANDALONE.bat").read_text(encoding="utf-8")
    assert "--include-package=pydicom" in source
    assert "pydicom_nuitka_plugins" not in source
    assert "pydicom.pixels.decoders.gdcm" not in source
