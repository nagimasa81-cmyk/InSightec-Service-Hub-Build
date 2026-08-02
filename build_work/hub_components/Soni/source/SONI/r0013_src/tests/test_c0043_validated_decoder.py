from pathlib import Path
import gzip, struct
import numpy as np
from src.services.hydrophone_replay_service import HydrophoneReplayService


def _write_valid_pair(root: Path):
    frames, ch, bins, fs = 3, 8, 256, 2_000_000
    header=struct.pack('<6I',100,frames,ch,16384,bins,fs)+b'\0'*8+struct.pack('<d',670_000.0)
    payload=bytearray()
    for f in range(frames):
        for c in range(ch):
            a=np.zeros(bins,dtype='<f4'); a[86+f]=c+1
            payload += struct.pack('<I',bins)+a.tobytes()+b'\0'*48
        payload += b'\0'*9368
    fft=root/'Spectrum_valid.dmp_FFT'
    with gzip.open(fft,'wb') as z:z.write(header+payload)
    raw=root/'Spectrum_valid.dmp'
    with gzip.open(raw,'wb') as z:z.write(struct.pack('<I',frames)+b'\0'*36+b'packet stream only')
    return [fft,raw]


def test_structural_fft_decoder_and_raw_rejection(tmp_path):
    replay=HydrophoneReplayService().build(_write_valid_pair(tmp_path),0,1)
    assert len(replay.frames)==3
    assert all(len(f.channels)==8 for f in replay.frames)
    assert not any(f.raw_channels for f in replay.frames)
    assert replay.decoder_confidence=='validated_fft'
    assert 'not verified' in replay.note


def test_no_equal_slice_heuristic_remains():
    text=(Path(__file__).parents[1]/'src/services/hydrophone_replay_service.py').read_text()
    assert 'len(payload) // frame_count' not in text
    assert 'strongest multi-channel variance' not in text
    assert 'validated_fft' in text
