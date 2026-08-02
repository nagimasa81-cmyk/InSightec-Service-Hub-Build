from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.services.discovery_service import DiscoveryService
from src.services.acoustic_control_service import AcousticControlService


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synchronized Temperature/Power/Score timing")
    parser.add_argument("dataset", type=Path, help="Extracted treatment folder")
    parser.add_argument("--sonication", type=int, default=5, help="1-based sonication number")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    workspace = args.dataset.resolve()
    package = DiscoveryService().discover(workspace, workspace)
    index = args.sonication - 1
    if index < 0 or index >= len(package.sonications):
        raise SystemExit(f"Sonication {args.sonication} is unavailable")
    son = package.sonications[index]
    duration = son.actual_duration_s or son.planned_duration_s
    if duration is None:
        raise SystemExit("No duration found in SonicationSummary.xml")
    trend = AcousticControlService().trend_for_sonication(
        package.workspace, index, son.replay_frame_count, duration
    )
    report = {
        "sonication": args.sonication,
        "actual_duration_s": son.actual_duration_s,
        "planned_duration_s": son.planned_duration_s,
        "planned_power_w": son.planned_power_w,
        "replay_frame_count": son.replay_frame_count,
        "frame_time_s": trend.time_s.tolist(),
        "power_percent": np.where(np.isfinite(trend.power_percent), trend.power_percent, np.nan).tolist(),
        "score_percent": np.where(np.isfinite(trend.score_percent), trend.score_percent, np.nan).tolist(),
        "acoustic_onset_raw_s": trend.acoustic_onset_raw_s,
        "cavitation_event_s": trend.cavitation_event_s,
        "modulation_event_s": list(trend.modulation_event_s),
        "status": trend.status,
    }
    text = json.dumps(report, indent=2, allow_nan=True)
    print(text)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
