from pathlib import Path
import gzip
import os

from src.services.import_service import ImportService
from src.services.discovery_service import DiscoveryService
from src.services.hydrophone_replay_service import HydrophoneReplayService


def test_c0045_static_contract():
    root = Path(__file__).parents[1]
    service = (root / "src/services/hydrophone_replay_service.py").read_text(encoding="utf-8")
    ui = (root / "src/ui/hydrophone_window.py").read_text(encoding="utf-8")
    assert "declared_message_count" in service
    assert "messages_per_snapshot" in service
    assert "raw_adc_unavailable_reason" in service
    assert "Measurement Timeline / Raw A/D" in ui
    assert 'if mode == "8 Panels":' in ui


def test_real_export_resolution_when_available():
    source = os.environ.get("SRE_TEST_EXPORT")
    if not source:
        return
    importer = ImportService(); workspace = importer.open(Path(source))
    try:
        package = DiscoveryService().discover(Path(source), workspace)
        service = HydrophoneReplayService()
        for index in range(len(package.sonications)):
            replay = service.build(package.cpc_spectrum_files, index, len(package.sonications))
            assert replay.frames
            assert len(replay.frames) == (replay.declared_message_count + 1) // 2
            assert replay.messages_per_snapshot == 2
            assert replay.raw_timeline_channels and len(replay.raw_timeline_channels) == 8
            assert replay.acquisition_interval_s > 0
            assert not replay.raw_adc_available
            assert "not present" in replay.raw_adc_unavailable_reason
    finally:
        importer.release(workspace)
