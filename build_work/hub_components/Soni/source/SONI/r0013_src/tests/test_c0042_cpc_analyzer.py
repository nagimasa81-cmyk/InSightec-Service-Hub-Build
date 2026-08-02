from pathlib import Path
import gzip
import struct
import numpy as np

from src.services.hydrophone_replay_service import HydrophoneReplayService


def _write_pair(root: Path):
    frame_count, channels, bins = 4, 8, 256
    header = struct.pack('<6I', 100, frame_count, channels, 16384, bins, 2_000_000)
    header += b'\0' * 8 + struct.pack('<d', 670_000.0)
    payload = bytearray()
    for frame in range(frame_count):
        for ch in range(channels):
            values = np.zeros(bins, dtype='<f4')
            values[80 + frame] = ch + 1
            payload += struct.pack('<I', bins) + values.tobytes() + b'\0' * 48
        payload += b'\0' * 9368
    fft = root/'Spectrum_test.dmp_FFT'
    with gzip.open(fft, 'wb') as stream: stream.write(header + payload)

    raw_header = struct.pack('<I', frame_count) + b'\0' * 36
    raw = root/'Spectrum_test.dmp'
    with gzip.open(raw, 'wb') as stream: stream.write(raw_header + b'packet stream only')
    return [fft, raw]


def test_cpc_analyzer_decodes_and_calculates(tmp_path):
    service = HydrophoneReplayService()
    replay = service.build(_write_pair(tmp_path), 0, 1)
    assert replay.channel_count == 8
    assert len(replay.frames) == 4
    assert len(replay.frames[0].raw_channels) == 0
    time, freq, image = service.spectrogram(replay, 0)
    assert image.shape[0] == 4
    assert image.shape[1] == len(freq)
    energy = service.band_energy(replay, 100_000, 500_000)
    assert energy.shape == (4, 8)
    stats = service.frame_statistics(replay, 0, 100_000, 500_000)
    assert len(stats) == 8
    assert np.isnan(stats[0]['raw_rms'])


def test_ui_contains_requested_analysis_tabs():
    text = (Path(__file__).parents[1]/'src/ui/hydrophone_window.py').read_text(encoding='utf-8')
    for label in ('Measurement Timeline / Raw A/D', 'Spectrum', 'Spectrogram', 'Band Energy', 'Measure / Statistics'):
        assert label in text
