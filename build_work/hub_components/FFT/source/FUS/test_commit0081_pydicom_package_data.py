from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_local_nuitka_build_includes_pydicom_package_data():
    text = (ROOT / "03_BUILD_NUITKA_STANDALONE.bat").read_text(encoding="utf-8")
    assert "--include-package-data=pydicom" in text
    assert "*urls.json" in text


def test_github_nuitka_builds_include_and_validate_package_data():
    workflow_names = [
        ".github/workflows/build_module_universal_v4.yml",
        ".github/workflows/build_selected_rc1.yml",
        ".github/workflows/build_selected_module_RC1_Runtime_Complete_R6.yml",
    ]
    for name in workflow_names:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "--include-package-data=pydicom" in text, name
        assert "*urls.json" in text, name
        assert "pydicom package data validation failed" in text, name


def test_lazy_decoder_architecture_is_preserved():
    launcher = (ROOT / "launcher.py").read_text(encoding="utf-8")
    decoder = (ROOT / "decoder_manager.py").read_text(encoding="utf-8")
    assert "register_packaged_plugins" not in launcher
    assert "pydicom.pixels.decoders.gdcm" not in launcher
    assert "import gdcm" not in decoder
