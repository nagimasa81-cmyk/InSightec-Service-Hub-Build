from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reverse_engineering.hydrophone_lab import HydrophoneReverseEngineeringLab


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze SpectrumMsg, Acquisition DMP, and Acquisition_Brain telemetry without changing Replay decoding.")
    parser.add_argument("source", type=Path, help="Extracted ANx folder, Sonication folder, or CPCFiles parent")
    parser.add_argument("--output", type=Path, default=None, help="Output directory (default: <source>/Hydrophone_RE_Report)")
    args = parser.parse_args()
    report = HydrophoneReverseEngineeringLab().analyze(args.source, args.output)
    print(f"HYDROPHONE_RE_OK files={len(report.files)} telemetry={len(report.telemetry)}")
    print(str((args.output or (args.source / 'Hydrophone_RE_Report')).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
