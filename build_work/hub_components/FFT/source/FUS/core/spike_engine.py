from dataclasses import dataclass
import numpy as np
@dataclass
class SpikeSettings:
    range_mode: str="Large"
    range_percent: int=100
    level: str="Wide"
@dataclass
class SpikeResult:
    detected: bool
    original: np.ndarray
    corrected: np.ndarray
    raw_before: np.ndarray
    raw_after: np.ndarray
    candidate_points: list
