from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.import_service import ImportService
from src.services.discovery_service import DiscoveryService
from src.services.hydrophone_replay_service import HydrophoneReplayService


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        raise SystemExit("Usage: python tools/audit_planning_hydrophone.py <treatment.zip|folder> [report.json]")
    source = Path(argv[0]).resolve()
    importer = ImportService(); workspace = importer.open(source)
    try:
        package = DiscoveryService().discover(source, workspace)
        service = HydrophoneReplayService()
        report = {"source": str(source), "planning": {}, "sonications": []}
        for asset in package.planning_assets:
            report["planning"].setdefault(asset.category, []).append({
                "path": str(asset.path.relative_to(workspace)), "role": asset.role,
                "confidence": asset.confidence, "notes": asset.notes,
            })
        for index, son in enumerate(package.sonications):
            replay = service.build(package.cpc_spectrum_files, index, len(package.sonications))
            report["sonications"].append({
                "name": son.name,
                "fft_source": replay.source_fft.name if replay.source_fft else None,
                "raw_source": replay.source_raw.name if replay.source_raw else None,
                "fft_snapshots": len(replay.frames),
                "declared_message_entries": replay.declared_message_count,
                "messages_per_fft_snapshot": replay.messages_per_snapshot,
                "final_snapshot_has_single_message": replay.final_snapshot_has_single_message,
                "fft_snapshot_coverage": (min(replay.declared_message_count, len(replay.frames) * replay.messages_per_snapshot) / replay.declared_message_count) if replay.declared_message_count else 0.0,
                "channels": replay.channel_count,
                "sample_rate_hz": replay.sampling_frequency_hz,
                "main_frequency_hz": replay.main_frequency_hz,
                "acquisition_interval_s": replay.acquisition_interval_s,
                "raw_adc_available": replay.raw_adc_available,
                "raw_adc_unavailable_reason": replay.raw_adc_unavailable_reason,
                "history_available": bool(replay.raw_timeline_channels),
                "history_samples_per_channel": len(replay.raw_timeline_channels[0]) if replay.raw_timeline_channels else 0,
                "history_channel_pairs": len(replay.raw_history_pairs),
                "raw_container_total_measurements": replay.raw_container_total_measurements,
                "raw_container_saved_measurements": replay.raw_container_saved_measurements,
                "raw_structure_note": replay.raw_structure_note,
                "decoder_confidence": replay.decoder_confidence,
                "decoder_note": replay.note,
            })
        out = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()/"planning_hydrophone_audit.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(out); return 0
    finally:
        importer.release(workspace)

if __name__ == "__main__":
    raise SystemExit(main())
