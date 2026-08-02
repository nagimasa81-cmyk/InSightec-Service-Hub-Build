from __future__ import annotations

import math
import struct
import tempfile
import json
from pathlib import Path

from src.integration.spectrum_provider import SpectrumMsgAnalyzerAdapter
from src.services.xd_ini_service import XdIniService
from src.services.acoustic_control_service import AcousticControlService
from src.services.sonication_frequency_service import SonicationFrequencyService
from src.services.sonication_channel_service import SonicationChannelService
from src.core.chart_state import ChartState
from src.reverse_engineering.hydrophone_lab import HydrophoneReverseEngineeringLab


def _verify_release_metadata() -> None:
    root = Path(__file__).resolve().parent
    version_text = (root / "VERSION").read_text(encoding="utf-8").strip()
    version_json = json.loads((root / "version.json").read_text(encoding="utf-8"))
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    from src.common.constants import APP_VERSION, APP_COMMIT

    assert version_text == APP_VERSION
    assert version_json["version"] == APP_VERSION
    assert version_json["commit"] == APP_COMMIT
    assert 'version = "2.0.15"' in pyproject
    assert 'RC2 R0015 Hub Dataset Auto-Load Fix' in pyproject


def main() -> int:
    _verify_release_metadata()
    with tempfile.TemporaryDirectory(
        prefix="SonicationReplayC0027_02bVerify_"
    ) as temp:
        root = Path(temp)

        ini = root / "Xd_ABC123.ini"
        ini.write_text(
            "[Transducer]\nSerial=ABC123\nMainFrequency=650 kHz\n",
            encoding="utf-8",
        )

        metadata = XdIniService().read_main_frequency(root)
        assert metadata.frequency_hz == 650000.0
        assert metadata.source_path == ini
        assert metadata.raw_line == "MainFrequency=650 kHz"

        son = root / "Sonication1"
        son.mkdir()
        act = son / "Sonication1.act"
        act.write_text("MainFrequency = 680 kHz\nAcoustic Channel = CH5\n", encoding="utf-8")
        local_frequency = SonicationFrequencyService().read(son)
        assert local_frequency.frequency_hz == 680000.0
        assert local_frequency.source == act
        channel = SonicationChannelService().read(son)
        assert channel.channel == 5
        state = ChartState(selected_channels={"CH5"}, user_selected_channels=True)
        assert state.selected_channels == {"CH5"}
        assert state.spectrum_mode == "Average"
        assert state.spectrum_average_window == 5

        values = []
        sample_count = 2048
        for index in range(sample_count):
            value = (
                math.exp(-((index - 930) / 20.0) ** 2) * 100.0
                + math.exp(-((index - 465) / 16.0) ** 2) * 25.0
                + math.exp(-((index - 1860) / 30.0) ** 2) * 40.0
            )
            values.append(struct.pack("<f", value))

        spectrum_file = son / "SpectrumMsg-1.dmp"
        spectrum_file.write_bytes(
            b"SPECTRUMMSG" + b"\x00" * 21 + b"".join(values)
        )

        adapter = SpectrumMsgAnalyzerAdapter(
            metadata.frequency_hz
        )
        frames = adapter.load([spectrum_file], source_kind="Sonication")

        assert len(frames) == 1
        assert frames[0].frequency
        assert frames[0].amplitude
        assert frames[0].main_peak_hz is not None
        assert frames[0].channel == 0
        assert frames[0].source_kind == "Sonication"
        assert abs(frames[0].main_peak_hz - 650000.0) < 100000.0

        acquisition = root / "Acquisition_Brain_650_Test.txt"
        acquisition.write_text(
            "08:00:00:000 Inf 1 StartSpectrumMeasurement: SetInitial PowerRatios: (1.000, 1.000)\n"
            "08:00:00:100 Inf 1 Set: AblPowerRatio = 0.8000 (200), Validity = 1\n"
            "08:00:00:110 Inf 1 Increase Power Rule: Calculated Energy: <0.001680>. Bottom Limit Of Harmless Energy: <0.014>\n",
            encoding="utf-8",
        )
        segments = AcousticControlService().parse_segments(acquisition)
        assert len(segments) == 1
        powers = [sample.power_percent for sample in segments[0].samples if sample.power_percent is not None]
        scores = [sample.score_percent for sample in segments[0].samples if sample.score_percent is not None]
        assert powers and abs(powers[-1] - 80.0) < 1e-6
        assert scores and abs(scores[-1] - 12.0) < 1e-6

        acquisition_dmp = root / "Acquisition_Test.dmp"
        acquisition_dmp.write_bytes(b"ACQUISITION\x00" + b"\x00" * 51 + b"".join(values))
        report_dir = root / "report"
        report = HydrophoneReverseEngineeringLab().analyze(root, report_dir)
        assert report.files
        assert report.telemetry
        assert (report_dir / "hydrophone_reverse_engineering_report.json").exists()
        assert (report_dir / "binary_candidates.csv").exists()
        assert any(item.family == "SpectrumMsg" for item in report.files)
        assert any(item.family == "Acquisition" for item in report.files)

    print("VERIFY_SOURCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
