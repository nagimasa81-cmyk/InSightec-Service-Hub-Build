from __future__ import annotations
from pathlib import Path
import numpy as np
from src.common.constants import IMAGE_SHAPE

class RawDecodeError(RuntimeError): pass

class RawService:
    def read_temperature(self,path:Path)->np.ndarray:
        data=np.fromfile(path,dtype='<f4')
        expected=IMAGE_SHAPE[0]*IMAGE_SHAPE[1]
        if data.size!=expected: raise RawDecodeError(f'Temperature RAW has {data.size} values; expected {expected}.')
        return data.reshape(IMAGE_SHAPE)
    def read_magnitude(self,path:Path)->np.ndarray:
        data=np.fromfile(path,dtype='<u2')
        expected=IMAGE_SHAPE[0]*IMAGE_SHAPE[1]
        if data.size!=expected: raise RawDecodeError(f'Magnitude RAW has {data.size} values; expected {expected}.')
        return data.reshape(IMAGE_SHAPE).astype(np.float32)
    @staticmethod
    def normalize_index(replay_index:int,replay_count:int,series_count:int)->int:
        if series_count<=1 or replay_count<=1: return 0
        return min(series_count-1,round(replay_index*(series_count-1)/(replay_count-1)))
