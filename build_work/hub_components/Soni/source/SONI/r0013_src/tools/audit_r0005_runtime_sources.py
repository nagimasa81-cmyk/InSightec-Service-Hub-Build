from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
import numpy as np

from src.services.import_service import ImportService
from src.services.discovery_service import DiscoveryService
from src.services.hydrophone_calibration_service import HydrophoneCalibrationService
from src.services.hydrophone_replay_service import HydrophoneReplayService
from src.integration.spectrum_provider import SpectrumMsgAnalyzerAdapter
from src.services.replay_service import ReplayService


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('R0005_RUNTIME_AUDIT.json'))
    args=parser.parse_args()
    importer=ImportService(); workspace=importer.open(args.source)
    package=DiscoveryService().discover(args.source, workspace)
    calibration=HydrophoneCalibrationService().read(package.workspace)
    ct=[a for a in package.planning_assets if getattr(a,'category','')=='PLANNING_CT' and getattr(a,'field_index',None)==16]
    son=package.sonications[0]
    replay=ReplayService()
    frame0=replay.frame(son,0)
    frame1=replay.frame(son,min(1,son.replay_frame_count-1))
    spectrum=SpectrumMsgAnalyzerAdapter(son.main_frequency_hz,calibration).load(son.spectrum_files)
    cpc=HydrophoneReplayService().build(package.cpc_spectrum_files,0,len(package.sonications))
    result={
        'sonication_count':len(package.sonications),
        'planning_ct_field16_count':len(ct),
        'planning_ct_first':str(ct[0].path) if ct else None,
        'calibration_available':calibration.available,
        'spectrum_factors':list(calibration.spectrum_factors),
        'spectrum_coef':calibration.spectrum_coef,
        'response_points':int(calibration.response_frequency_hz.size),
        'mr_replay_frame_count':son.replay_frame_count,
        'magnitude_frame_count':len(son.magnitude_frames),
        'temperature_frame_count':len(son.temperature_frames),
        'spectrum_file_count':len(son.spectrum_files),
        'roi_pixel_count':int(replay._roi_mask((256,256)).sum()),
        'main_frame0_magnitude_shape':list(frame0.magnitude.shape) if frame0.magnitude is not None else None,
        'main_frame1_magnitude_shape':list(frame1.magnitude.shape) if frame1.magnitude is not None else None,
        'main_frame_change_max_abs':float(np.max(np.abs(frame1.magnitude-frame0.magnitude))) if frame0.magnitude is not None and frame1.magnitude is not None else None,
        'sonication_spectrum_frame_count':len(spectrum),
        'sonication_spectrum_channels':dict(Counter(str(f.channel) for f in spectrum)),
        'cpc_frame_count':len(cpc.frames),
        'cpc_channel_count':len(cpc.frames[0].channels) if cpc.frames else 0,
        'cpc_calibration_reported':'Calibration applied' in cpc.note,
    }
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    required=(len(ct)>0 and calibration.available and frame0.magnitude is not None and
              result['main_frame_change_max_abs'] not in (None,0.0) and result['roi_pixel_count']==9 and result['mr_replay_frame_count']==max(result['magnitude_frame_count'],result['temperature_frame_count'],1) and len(spectrum)>0 and
              len(cpc.frames)>0 and result['cpc_channel_count']==8 and result['cpc_calibration_reported'])
    return 0 if required else 2

if __name__=='__main__': raise SystemExit(main())
