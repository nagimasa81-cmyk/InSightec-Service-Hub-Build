from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import numpy as np

from src.parsers.ado_rowset import parse_ado_rowset


@dataclass(slots=True)
class SonicationMetadata:
    summary: dict[str, str] = field(default_factory=dict)
    mr: list[tuple[str, str]] = field(default_factory=list)
    scan: list[tuple[str, str]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


class SonicationMetadataService:
    """Resolve display metadata from the full export, not only the Sonication folder."""

    DQA_FALLBACK = {
        1: ("Axial", "A/P", "R/L"),
        2: ("Sagittal", "A/P", "S/I"),
        3: ("Axial", "R/L", "A/P"),
    }


    def _row_for_sonication(self, path: Path, sonication_number: int) -> dict[str, object]:
        """Return only a real ADO z:row for the requested sonication."""
        if not path.exists():
            return {}
        try:
            rows = parse_ado_rowset(path)
        except (ET.ParseError, OSError, ValueError):
            return {}
        keys = ("sonicationindex", "sonication", "sonicationnumber", "sonicationno", "index")
        for row in rows:
            for key in keys:
                value = row.get(key)
                try:
                    if value is not None and int(float(value)) == int(sonication_number):
                        return row
                except (TypeError, ValueError):
                    continue
        # Some ADO exports store rows strictly in sonication order without an index column.
        data_rows = [row for row in rows if any(k in row for k in ("seriesuid", "name", "poweron", "sonicationduration", "imgmatrixx"))]
        index = int(sonication_number) - 1
        return data_rows[index] if 0 <= index < len(data_rows) else {}

    @staticmethod
    def _orientation_from_cosines(row: dict[str, object]) -> str | None:
        try:
            r = np.asarray([float(row[k]) for k in ("rowdirectcosrasx", "rowdirectcosrasy", "rowdirectcosrasz")])
            c = np.asarray([float(row[k]) for k in ("coldirectcosrasx", "coldirectcosrasy", "coldirectcosrasz")])
        except (KeyError, TypeError, ValueError):
            return None
        n = np.cross(r, c)
        if not np.all(np.isfinite(n)) or np.linalg.norm(n) < 1e-6:
            return None
        axis = int(np.argmax(np.abs(n)))
        return ("Sagittal", "Coronal", "Axial")[axis]

    @staticmethod
    def _f(row, key):
        try: return float(row[key])
        except (KeyError,TypeError,ValueError): return None

    def read(self, model, package, sonication_number: int) -> SonicationMetadata:
        workspace = Path(package.workspace)
        texts = self._text_files(workspace)
        mr_path=self._find_first(workspace,["MriImageParams.xml","MRIImageParams.xml"])
        protocol_path=self._find_first(workspace,["ProtocolData.xml"])
        mr_row=self._row_for_sonication(mr_path,sonication_number) if mr_path else {}
        protocol_row=self._row_for_sonication(protocol_path,sonication_number) if protocol_path else {}
        sources: list[str] = []

        orientation = self._search(texts, [r"(?:Scan\s*Plane|Orientation|Plane)\s*[:=]\s*([A-Za-z/]+)"])
        freq_dir = self._search(texts, [r"(?:Frequency\s*(?:Dir|Direction)|FreqDir)\s*[:=]\s*([A-Za-z/]+)"])
        hotspot = "Unavailable"
        if sonication_number in self.DQA_FALLBACK:
            o, f, hotspot = self.DQA_FALLBACK[sonication_number]
            orientation = orientation or o
            freq_dir = freq_dir or f

        power = model.planned_power_w
        # ProtocolData.poweron is a percentage, not watts. Do not mislabel it as W.
        duration = model.actual_duration_s or model.planned_duration_s
        if duration is None: duration=self._f(protocol_row,"sonicationduration")
        energy = power * duration if power is not None and duration is not None else None
        frequency_hz = model.main_frequency_hz or getattr(package, "main_frequency_hz", None)

        orientation = orientation or self._orientation_from_cosines(mr_row)
        freq_dir = freq_dir or mr_row.get("freqdirection")
        summary = {
            "Orientation": self._normal(orientation),
            "Frequency Dir": self._normal_dir(freq_dir),
            "Energy": f"{energy:.1f} J" if energy is not None else "Unavailable",
            "Power": f"{power:.1f} W" if power is not None else "Unavailable",
            "Duration": f"{duration:.3f} s" if duration is not None else "Unavailable",
            "Frequency": f"{frequency_hz/1e6:.3f} MHz" if frequency_hz else "Unavailable",
            "Hotspot Check": hotspot,
        }

        review = self._find_first(workspace, ["review.out", "review.out.ar"])
        review_text = self._read(review) if review else ""
        if review: sources.append(str(review))
        mr = self._review_rows(review_text)
        xml_mr=[("Series Description",mr_row.get("seriesdiscription")),("Manufacturer",mr_row.get("manufacturer")),("Matrix",f"{mr_row.get('imgmatrixx','?')} x {mr_row.get('imgmatrixy','?')}"), ("Slice Thickness",mr_row.get("slicethick")),("Pixel Size",f"{mr_row.get('pixsizex','?')} x {mr_row.get('pixsizey','?')}"),("TR",mr_row.get("repetitiontimetr")),("TE",mr_row.get("echotimete")),("Flip Angle",mr_row.get("mrflipangle")),("Frequency Direction",mr_row.get("freqdirection")),("Series UID",mr_row.get("seriesuid"))]
        existing={k for k,_ in mr}
        mr.extend((k,str(v)) for k,v in xml_mr if v not in (None,"") and k not in existing)
        if not mr:
            mr = [("Status", "MR information was not decoded from review.out")]
        mr.extend([
            ("Replay Orientation", summary["Orientation"]),
            ("Frequency Direction", summary["Frequency Dir"]),
            ("Temperature RAW Frames", str(len(model.temperature_frames))),
            ("Magnitude RAW Frames", str(len(model.magnitude_frames))),
        ])

        act = model.act_files[0] if model.act_files else None
        if act: sources.append(str(act))
        scan = [
            ("Protocol Name", protocol_row.get("name","Unavailable")),
            ("SVAT Protocol", protocol_row.get("svatprotocolname","Unavailable")),
            ("Planned Power %", f"{protocol_row.get('poweron')} %" if protocol_row.get("poweron") is not None else "Unavailable"),
            ("Planned Duration", protocol_row.get("sonicationduration","Unavailable")),
            ("Cooling Duration", protocol_row.get("coolingdurationl","Unavailable")),
            ("Dose Threshold", protocol_row.get("dosetreshold","Unavailable")),
            ("Spot Diameter", protocol_row.get("spotdiameter","Unavailable")),
            ("Sonication", str(sonication_number)),
            ("Orientation", summary["Orientation"]),
            ("Frequency Direction", summary["Frequency Dir"]),
            ("Hotspot Check Direction", hotspot),
            ("Power", summary["Power"]),
            ("Duration", summary["Duration"]),
            ("Energy", summary["Energy"]),
            ("Transducer Frequency", summary["Frequency"]),
            ("ACT File", act.name if act else "Unavailable"),
            ("ACT Elements", self._act_element_count(act)),
            ("SpectrumMsg Files", str(len(model.spectrum_files))),
            ("Temperature RAW Frames", str(len(model.temperature_frames))),
        ]
        return SonicationMetadata(summary=summary, mr=mr, scan=scan, sources=sources)

    def _text_files(self, workspace: Path):
        result=[]
        for p in workspace.rglob("*"):
            if p.is_file() and (p.suffix.lower() in {".log", ".txt", ".act", ".ini"} or p.name.lower().startswith("review.out")):
                result.append(p)
        return result

    def _search(self, paths, patterns):
        compiled=[re.compile(p,re.I) for p in patterns]
        for path in paths:
            text=self._read(path)
            for pattern in compiled:
                m=pattern.search(text)
                if m: return m.group(1).strip()
        return None

    def _find_first(self, root: Path, names):
        lower={n.lower() for n in names}
        matches=[p for p in root.rglob("*") if p.is_file() and p.name.lower() in lower]
        return sorted(matches, key=lambda p:(names.index(p.name.lower()) if p.name.lower() in names else 99, len(p.parts)))[0] if matches else None

    def _read(self, path):
        if not path: return ""
        try: return path.read_text(encoding="utf-8", errors="ignore")
        except OSError: return ""

    def _review_rows(self, text: str):
        if not text: return []
        specs = [
            ("Scanner Mode", r"Scanner Mode\s*:\s*([^\t\r\n]+)"),
            ("Patient Position", r"Position\s*:\s*([^\t\r\n]+)"),
            ("Coil Name", r"Coil Name\s*:\s*([^\t\r\n]+)"),
            ("Protocol", r"Protocol\s*:\s*([^\t\r\n]+)"),
            ("Series Description", r"Series De\s*:\s*([^\t\r\n]+)"),
            ("PSD Name", r"Psd Name\s*:\s*([^\t\r\n]+)"),
            ("TE", r"Echo Time \(TE\)\s*:\s*([^\t\r\n]+)"),
            ("TR", r"Rep Time \(TR\)\s*:\s*([^\t\r\n]+)"),
            ("FOV", r"Field of View\s*:\s*([^\t\r\n]+)"),
            ("Slice Thickness", r"Slice Thickness\s*:\s*([^\t\r\n]+)"),
            ("Acquisition Matrix", r"Acq\. Matrix\s*:\s*([^\t\r\n]+)"),
        ]
        rows=[]
        for label, pat in specs:
            m=re.search(pat,text,re.I)
            if m: rows.append((label, re.sub(r"\s+", " ", m.group(1)).strip()))
        return rows

    def _act_element_count(self, path):
        text=self._read(path)
        m=re.search(r"NumberOfElements\s*=\s*(\d+)",text,re.I)
        return m.group(1) if m else "Unavailable"

    def _normal(self, value):
        if not value: return "Unavailable"
        v=value.strip().replace("SAGITAL","SAGITTAL")
        return v.title()

    def _normal_dir(self, value):
        return value.strip().upper() if value else "Unavailable"
