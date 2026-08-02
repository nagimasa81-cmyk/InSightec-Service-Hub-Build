from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import xml.etree.ElementTree as ET


@dataclass(slots=True)
class PlanningAsset:
    category: str
    path: Path
    role: str
    confidence: float
    notes: str = ""
    width: int | None = None
    height: int | None = None
    dtype: str | None = None
    field_index: int | None = None
    sonication_index: int | None = None
    zone_index: int | None = None
    array_index: int | None = None


@dataclass(slots=True)
class PlanningDataSummary:
    assets: list[PlanningAsset] = field(default_factory=list)

    def by_category(self, category: str) -> list[PlanningAsset]:
        return [item for item in self.assets if item.category == category]

    @property
    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.assets:
            result[item.category] = result.get(item.category, 0) + 1
        return result


class PlanningDataService:
    """Classify planning/reference resources without treating them as replay frames."""

    _RAW_RE = re.compile(r"^(\d+)-.*-(\d+)\.raw$", re.I)


    def _ct_linked_raws(self, workspace: Path) -> list[PlanningAsset]:
        """Resolve actual planning CT image payloads from CtImage.xml.

        CtImage.xml indexes many image families, including thermometry and anatomy.
        Planning CT is restricted to 512 x 512 records.  Field 16 is the signed
        CT/HU-like volume and is sorted first; other 512 x 512 CT-derived fields
        remain available after it.
        """
        xml_path = next((p for p in workspace.rglob("*") if p.is_file() and p.name.lower() == "ctimage.xml"), None)
        if xml_path is None:
            return []
        sonication_dirs = {
            int(match.group(1)): directory
            for directory in workspace.rglob("*")
            if directory.is_dir() and (match := re.fullmatch(r"sonication[_-]?(\d+)", directory.name, re.I))
        }
        assets: list[PlanningAsset] = []
        try:
            from src.parsers.ado_rowset import parse_ado_rowset
            rows = parse_ado_rowset(xml_path)
        except (ET.ParseError, OSError, ValueError):
            return []
        for row in rows:
            try:
                field = int(row.get("fieldindex", -1)); son = int(row.get("sonicationindex", -1))
                zone = int(row.get("zoneindex", 0)); arr = int(row.get("arrayindex", 0))
                sx = int(row.get("imagesize_x", 0)); sy = int(row.get("imagesize_y", 0))
            except (TypeError, ValueError):
                continue
            # This export's planning CT families are 512 x 512.  Exclude the
            # 256 x 256 TMAP/MR replay families that were previously mislabeled CT.
            if sx != 512 or sy != 512:
                continue
            folder = sonication_dirs.get(son)
            if folder is None:
                continue
            candidates = [
                folder / f"{field}-1-{zone}-{arr}.raw",
                folder / f"{field}-1-0-{arr}.raw",
                folder / f"{field}-0-{zone}-{arr}.raw",
                folder / f"{field}-0-0-{arr}.raw",
            ]
            raw = next((candidate for candidate in candidates if candidate.exists()), None)
            if raw is None:
                continue
            elements = sx * sy
            if raw.stat().st_size != elements * 2:
                continue
            dtype = "<i2" if field == 16 else "<u2"
            role = "Planning CT (signed CT/HU volume)" if field == 16 else f"Planning CT derived image (field {field})"
            confidence = 0.995 if field == 16 else 0.92
            assets.append(PlanningAsset(
                "PLANNING_CT", raw, role, confidence,
                f"CtImage row field={field}, sonication={son}, zone={zone}, array={arr}, {sx}x{sy}, dtype={dtype}",
                sx, sy, dtype, field, son, zone, arr,
            ))
        unique: dict[Path, PlanningAsset] = {asset.path: asset for asset in assets}
        return sorted(unique.values(), key=lambda item: (
            0 if item.field_index == 16 else 1,
            item.field_index or 999, item.sonication_index or 999, item.array_index or 0,
        ))

    def discover(self, workspace: Path) -> PlanningDataSummary:
        assets: list[PlanningAsset] = []
        assets.extend(self._ct_linked_raws(workspace))
        son1 = next((p for p in workspace.rglob("*") if p.is_dir() and p.name.lower().replace("_", "") == "sonication1"), None)

        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            low_name = path.name.lower()
            low_path = str(path).lower().replace("\\", "/")
            category = role = notes = ""
            confidence = 0.0

            if low_name in {"ctimage.xml", "ctvolumedata.xml"}:
                category, role, confidence = "PLANNING_METADATA", "CT volume metadata used by skull/SDR planning", 1.0
            elif "skullmeasure" in low_name or "bonespot" in low_name or "sdr" in low_name:
                category, role, confidence = "SDR_DATA", "Skull/SDR calculation input or result", 0.95
            elif low_name.startswith("ctmr") or "ctmrregistration" in low_name:
                category, role, confidence = "REGISTRATION_DATA", "CT-to-MR registration", 0.98
            elif low_name.startswith("mrmr") or "mrmrregistration" in low_name:
                category, role, confidence = "REGISTRATION_DATA", "MR-to-MR registration", 0.98
            elif low_name == "mriimageparams.xml" or "mi_params" in low_name or low_name.startswith("miparams"):
                category, role, confidence = "PRE_TREATMENT_MR", "MR acquisition/reference metadata", 0.90
            elif "/sonication1/" in low_path and self._RAW_RE.match(path.name):
                prefix = self._RAW_RE.match(path.name).group(1)
                if prefix not in {"5", "6"}:
                    category, role, confidence = "PRE_TREATMENT_MR", f"Sonication1 non-replay RAW series (prefix {prefix})", 0.85
                    notes = "Kept separate from thermometry/magnitude replay until image semantics are verified."
            elif son1 is not None and path.parent == son1 and path.suffix.lower() in {".rgs", ".txt"} and ("fid" in low_name or "mat" in low_name):
                category, role, confidence = "REGISTRATION_DATA", "Planning registration matrix/fiducials", 0.90

            if category:
                assets.append(PlanningAsset(category, path, role, confidence, notes))

        def _asset_sort_key(item: PlanningAsset):
            # Keep the verified signed CT/HU stack (field 16) first and preserve
            # numeric slice order.  The previous final lexical sort silently
            # destroyed _ct_linked_raws() ordering, so field 12 appeared first
            # and slices such as 100 were placed before 11.
            if item.category == "PLANNING_CT":
                field_priority = 0 if item.field_index == 16 else 1
                return (
                    0,
                    field_priority,
                    item.field_index if item.field_index is not None else 999,
                    item.sonication_index if item.sonication_index is not None else 999,
                    item.zone_index if item.zone_index is not None else 999,
                    item.array_index if item.array_index is not None else 999999,
                    str(item.path).lower(),
                )
            return (1, item.category, 0, 0, 0, 0, str(item.path).lower())

        assets.sort(key=_asset_sort_key)
        return PlanningDataSummary(assets)
