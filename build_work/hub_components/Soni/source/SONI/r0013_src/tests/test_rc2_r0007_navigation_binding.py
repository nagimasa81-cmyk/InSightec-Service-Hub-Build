from pathlib import Path

from src.domain.models import RawFrame, SonicationModel
from src.services.replay_service import ReplayService


def test_replay_timeline_is_owned_by_mr_not_spectrum(tmp_path: Path):
    son = SonicationModel(name="S1", folder=tmp_path)
    son.magnitude_frames = [RawFrame(tmp_path / f"m{i}.raw", i, "m") for i in range(7)]
    son.temperature_frames = [RawFrame(tmp_path / f"t{i}.raw", i, "t") for i in range(6)]
    son.spectrum_files = [tmp_path / f"SpectrumMsg-{i}.dmp" for i in range(51)]
    assert son.replay_frame_count == 7


def test_roi_is_exactly_three_by_three_pixels():
    cx, cy, width, height = ReplayService._roi_geometry((256, 256))
    assert (width, height) == (3.0, 3.0)
    mask = ReplayService._roi_mask((256, 256))
    # With a half-pixel center on an even-sized image, the inclusive square is 4x4
    # unless geometry is interpreted carefully. The required voxel must contain
    # exactly nine pixels, so the mask implementation is checked directly.
    assert int(mask.sum()) == 9


def test_thumbnail_activation_and_inverse_mapping_are_present():
    source = Path("src/ui/main_window.py").read_text(encoding="utf-8")
    assert "itemClicked.connect" in source
    assert "def _unified_image_item_selected" in source
    assert "def _map_data_to_replay" in source
    assert "self._map_data_to_replay" in source
    assert "3 pixels × 3 pixels" in source
