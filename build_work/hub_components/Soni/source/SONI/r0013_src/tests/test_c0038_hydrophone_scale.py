import numpy as np
from src.services.hydrophone_replay_service import CpcHydrophoneReplay

def test_c0038_fixed_display_scale_defaults():
    replay=CpcHydrophoneReplay(source_fft=None,source_raw=None)
    assert replay.display_db_min == -60.0
    assert replay.display_db_max == 0.0
    assert len(replay.channel_reference_levels) == 8
    assert all(np.isfinite(v) and v > 0 for v in replay.channel_reference_levels)
