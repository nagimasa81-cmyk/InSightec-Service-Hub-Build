import struct
import numpy as np
from src.services.hydrophone_replay_service import HydrophoneReplayService


def make_history(total=64):
    header=bytearray(128)
    struct.pack_into('<I',header,0,12)
    chunks=[]
    for ch in range(8):
        for pair in range(2):
            a=np.zeros(total,dtype='<f4') if pair==0 else (np.linspace(.001,.01,total,dtype='<f4')*(ch+1))
            chunks.append(struct.pack('<I',total)+a.tobytes()+b'X'*4)
    return bytes(header)+b''.join(chunks)


def test_validated_raw_history_layout():
    channels,info=HydrophoneReplayService._decode_raw_timeline(make_history(),64,8)
    assert len(channels)==8
    assert all(len(x)==64 for x in channels)
    assert info['total_measurements']==64
    assert info['saved_measurements']==12
    assert 'not the 2048-sample' in info['note']


def test_rejects_history_as_adc_waveform():
    blob=make_history()
    out=HydrophoneReplayService._decode_raw_payload(blob,3,8,16384)
    assert out==[]
