from __future__ import annotations
import json, re
from pathlib import Path
from .models import MRMetadata, SkullMetadata, SonicationMetadata, SourceStatus, StudyMetadata
from ...parsers.ado_rowset import parse_ado_rowset
from ...parsers.review_out_parser import parse as parse_review
from ...parsers.skull_measure_parser import parse_header_and_count

class MetadataManager:
    XML_SOURCES = {
        "summary": "SonicationSummary.xml",
        "protocol": "ProtocolData.xml",
        "spot": "SpotData.xml",
        "treatment": "FusTreatmentData.xml",
        "layer": "LayerData.xml",
        "study": "FusStudyData.xml",
    }

    def load(self, root: str | Path) -> StudyMetadata:
        root = Path(root).resolve()
        result = StudyMetadata(root=str(root))
        parsed: dict[str, list[dict]] = {}
        for key, filename in self.XML_SOURCES.items():
            matches = list(root.rglob(filename))
            status = SourceStatus()
            result.sources[key] = status
            if not matches:
                result.warnings.append(f"Missing {filename}")
                continue
            status.path = str(matches[0])
            try:
                rows = parse_ado_rowset(matches[0])
                parsed[key] = rows
                status.loaded = True
                status.records = len(rows)
            except Exception as exc:
                status.error = f"{type(exc).__name__}: {exc}"
        if parsed.get("study"):
            result.study = parsed["study"][0]
        summary_rows = parsed.get("summary", [])
        indexes = sorted({self._sonication_index(r) for r in summary_rows if self._sonication_index(r) is not None})
        if not indexes:
            indexes = self._discover_folder_indexes(root)
        protocol_rows = parsed.get("protocol", [])
        spot_rows = parsed.get("spot", [])
        treatment = parsed.get("treatment", [{}])[0] if parsed.get("treatment") else {}
        layer_rows = parsed.get("layer", [])
        review_path = next(iter(root.rglob("review.out")), None)
        mr = MRMetadata()
        if review_path:
            try:
                mr.fields = parse_review(review_path)
                mr.source = SourceStatus(str(review_path), True, 1, None)
            except Exception as exc:
                mr.source = SourceStatus(str(review_path), False, 0, str(exc))
        result.mr = mr
        for index in indexes:
            summary = next((r for r in summary_rows if self._sonication_index(r) == index), {})
            spots = [r for r in spot_rows if self._sonication_index(r) == index]
            protocols = [r for r in protocol_rows if self._row_matches_sonication(r, index)]
            layers = [r for r in layer_rows if self._row_matches_sonication(r, index)]
            skull = self._load_skull(root, index, spots)
            son = SonicationMetadata(index=index, summary=summary, protocol=(protocols[0] if protocols else {}), spots=spots, treatment=treatment, layer=(layers[0] if layers else {}), mr=mr, skull=skull)
            son.sources = dict(result.sources)
            result.sonications[index] = son
        return result

    def export_json(self, metadata: StudyMetadata, path: str | Path) -> None:
        Path(path).write_text(json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    @staticmethod
    def _sonication_index(row: dict) -> int | None:
        for key in ("sonicationindex", "sonication", "sonicindex", "sonicnum", "sonicationnumber"):
            value = row.get(key)
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                pass
        return None

    def _row_matches_sonication(self, row: dict, index: int) -> bool:
        found = self._sonication_index(row)
        return found == index if found is not None else False

    @staticmethod
    def _discover_folder_indexes(root: Path) -> list[int]:
        values = set()
        for p in root.rglob("*"):
            m = re.fullmatch(r"Sonication\s*(\d+)", p.name, re.I)
            if m:
                values.add(int(m.group(1)))
        return sorted(values)

    def _load_skull(self, root: Path, index: int, spots: list[dict]) -> SkullMetadata:
        skull = SkullMetadata()
        cues = {str(r.get(k)) for r in spots for k in ("spotcue", "cue", "spotid") if r.get(k) is not None}
        skull.spot_cues = sorted(cues)
        candidates = list(root.rglob(f"SkullMeasures_sonic{index}_cue*.log"))
        for path in candidates:
            if cues and not any(cue in path.name for cue in cues):
                continue
            _, count = parse_header_and_count(path)
            skull.files.append(str(path))
            skull.element_counts[path.name] = count
        return skull
