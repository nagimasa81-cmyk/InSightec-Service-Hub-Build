from pathlib import Path


def test_decoder_is_lazy_and_diagnostic():
    text = Path('decoder_manager.py').read_text(encoding='utf-8')
    assert 'import gdcm' not in text
    assert 'pydicom.pixels.decoders.gdcm' not in text
    assert 'decoder_capabilities' in text
    assert 'dicom_decoder.log' in text
    assert 'decode_success' in text and 'decode_failure' in text


def test_dicom_sort_key_remains_series_stable():
    text = Path('app.py').read_text(encoding='utf-8')
    assert "sort_key = (series, z, instance, path.name.lower())" in text
    assert "MR_IMAGE_DICOM_CACHE" in text


def test_packaged_pydicom_data_validation_remains_enabled():
    text = Path('03_BUILD_NUITKA_STANDALONE.bat').read_text(encoding='utf-8', errors='ignore')
    assert '--include-package-data=pydicom' in text
    assert '*urls.json' in text
