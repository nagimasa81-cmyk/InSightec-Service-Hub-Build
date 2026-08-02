from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.discovery_service import DiscoveryService
from src.services.import_service import ImportService
from src.services.replay_service import ReplayService


def audit(source: Path) -> dict:
    importer = ImportService()
    workspace = importer.open(source)
    package = DiscoveryService().discover(source, workspace)
    replay = ReplayService()
    sonications = []
    for son in package.sonications:
        first = replay.frame(son, 0) if son.replay_frame_count else None
        sonications.append({
            "name": son.name,
            "replay_frames": son.replay_frame_count,
            "magnitude_frames": len(son.magnitude_frames),
            "temperature_frames": len(son.temperature_frames),
            "spectrum_files": len(son.spectrum_files),
            "act_files": len(son.act_files),
            "main_frequency_hz": son.main_frequency_hz,
            "first_magnitude_shape": list(first.magnitude.shape) if first and first.magnitude is not None else None,
            "first_temperature_shape": list(first.temperature.shape) if first and first.temperature is not None else None,
            "temperature_source": first.temperature_source if first else "Unavailable",
        })
    report = {
        "source": str(source.resolve()),
        "workspace": str(workspace.resolve()),
        "sonication_count": len(package.sonications),
        "cpc_spectrum_file_count": len(package.cpc_spectrum_files),
        "sonications": sonications,
    }
    importer.cleanup()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a Sonication Replay treatment folder.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.source)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["sonication_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
