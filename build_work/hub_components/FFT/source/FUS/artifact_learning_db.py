from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

DEFAULT_ARTIFACT_TYPES = [
    "Spike", "Frequency", "Ghosting", "Motion", "Wraparound",
    "Shading", "Dropout", "Not Artifact",
]
DEFAULT_RESOLUTIONS = [
    "No action required", "Reacquired image", "Changed sequence parameters",
    "Adjusted frequency", "Removed external interference", "Repositioned tracker",
    "Restarted system", "Hardware service",
]

def image_features(image: np.ndarray, normal_image: np.ndarray | None = None) -> dict:
    arr = np.asarray(image, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        finite = np.array([0.0])
    centered = np.nan_to_num(arr - np.nanmean(arr))
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(centered)))
    sf = spectrum[np.isfinite(spectrum)]
    if sf.size == 0:
        sf = np.array([0.0])
    result = {
        "shape": list(arr.shape),
        "mean": float(np.nanmean(arr)),
        "std": float(np.nanstd(arr)),
        "min": float(np.nanmin(finite)),
        "max": float(np.nanmax(finite)),
        "p01": float(np.nanpercentile(finite, 1)),
        "p50": float(np.nanpercentile(finite, 50)),
        "p99": float(np.nanpercentile(finite, 99)),
        "rms": float(np.sqrt(np.nanmean(arr ** 2))),
        "fft_peak": float(np.nanmax(sf)),
        "fft_median": float(np.nanmedian(sf)),
        "fft_peak_ratio": float(np.nanmax(sf) / max(np.nanmedian(sf), np.finfo(float).eps)),
        "normal_comparison": False,
    }
    if normal_image is not None:
        normal = np.asarray(normal_image, dtype=np.float64)
        if normal.shape == arr.shape:
            diff = arr - normal
            result.update({
                "normal_comparison": True,
                "difference_mean": float(np.nanmean(diff)),
                "difference_std": float(np.nanstd(diff)),
                "difference_rms": float(np.sqrt(np.nanmean(diff ** 2))),
                "difference_abs_mean": float(np.nanmean(np.abs(diff))),
                "difference_abs_max": float(np.nanmax(np.abs(diff))),
            })
        else:
            result["normal_shape_mismatch"] = list(normal.shape)
    return result

class ArtifactDatabase:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()
        self._seed_defaults()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def close(self):
        self.connection.close()

    def _create_schema(self):
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS artifact_types(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resolutions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS samples(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT,
            source_name TEXT NOT NULL,
            series_uid TEXT,
            series_description TEXT,
            instance_number INTEGER,
            artifact_type TEXT NOT NULL,
            resolution TEXT,
            is_normal_reference INTEGER NOT NULL DEFAULT 0,
            normal_reference_path TEXT,
            features_json TEXT NOT NULL,
            notes TEXT,
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );
        """)
        self.connection.commit()

    def _seed_defaults(self):
        for name in DEFAULT_ARTIFACT_TYPES:
            self.add_artifact_type(name)
        for name in DEFAULT_RESOLUTIONS:
            self.add_resolution(name)

    def add_artifact_type(self, name: str):
        value = name.strip()
        if value:
            self.connection.execute(
                "INSERT OR IGNORE INTO artifact_types(name, created_utc) VALUES (?,?)",
                (value, self._now()),
            )
            self.connection.commit()

    def add_resolution(self, name: str):
        value = name.strip()
        if value:
            self.connection.execute(
                "INSERT OR IGNORE INTO resolutions(name, created_utc) VALUES (?,?)",
                (value, self._now()),
            )
            self.connection.commit()

    def artifact_types(self):
        return [r["name"] for r in self.connection.execute(
            "SELECT name FROM artifact_types WHERE active=1 ORDER BY name"
        )]

    def resolutions(self):
        return [r["name"] for r in self.connection.execute(
            "SELECT name FROM resolutions WHERE active=1 ORDER BY name"
        )]

    def add_sample(self, **sample):
        now = self._now()
        cur = self.connection.execute("""
        INSERT INTO samples(
            source_path, source_name, series_uid, series_description, instance_number,
            artifact_type, resolution, is_normal_reference, normal_reference_path,
            features_json, notes, created_utc, updated_utc
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            sample.get("source_path",""), sample.get("source_name",""),
            sample.get("series_uid",""), sample.get("series_description",""),
            int(sample.get("instance_number",0)), sample.get("artifact_type","Not Artifact"),
            sample.get("resolution",""), 1 if sample.get("is_normal_reference") else 0,
            sample.get("normal_reference_path",""),
            json.dumps(sample.get("features",{}), ensure_ascii=False),
            sample.get("notes",""), now, now
        ))
        self.connection.commit()
        return int(cur.lastrowid)

    def update_sample_classification(self, sample_id, artifact_type, resolution, notes):
        self.connection.execute("""
        UPDATE samples SET artifact_type=?, resolution=?, notes=?, updated_utc=? WHERE id=?
        """, (artifact_type, resolution, notes, self._now(), int(sample_id)))
        self.connection.commit()

    def samples(self):
        return [dict(r) for r in self.connection.execute(
            "SELECT * FROM samples ORDER BY updated_utc DESC, id DESC"
        )]

    def samples_by_type(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for sample in self.samples():
            grouped.setdefault(str(sample["artifact_type"]), []).append(sample)
        return grouped

    def training_feature_vectors(self) -> tuple[list[str], np.ndarray, list[str], dict]:
        """
        Return numeric training vectors from stored feature JSON.

        The selected feature keys are stable and shared by image and raw screening.
        Missing values are represented by NaN and later imputed by the detector.
        """
        keys = [
            "mean", "std", "min", "max", "p01", "p50", "p99", "rms",
            "fft_peak", "fft_median", "fft_peak_ratio",
            "difference_mean", "difference_std", "difference_rms",
            "difference_abs_mean", "difference_abs_max",
        ]
        vectors = []
        labels = []
        metadata = {"keys": keys, "sample_ids": []}

        for sample in self.samples():
            raw = sample.get("features_json", "{}")
            try:
                features = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except Exception:
                continue

            vector = []
            for key in keys:
                value = features.get(key, np.nan)
                try:
                    vector.append(float(value))
                except Exception:
                    vector.append(np.nan)

            vectors.append(vector)
            labels.append(str(sample.get("artifact_type", "Not Artifact")))
            metadata["sample_ids"].append(int(sample["id"]))

        if not vectors:
            return keys, np.empty((0, len(keys)), dtype=float), [], metadata
        return keys, np.asarray(vectors, dtype=float), labels, metadata

    def export_json(self, path: Path):
        payload = {
            "schema": "MRI_Raw_FFT_Artifact_DB",
            "version": 1,
            "artifact_types": self.artifact_types(),
            "resolutions": self.resolutions(),
            "samples": self.samples(),
        }
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_json(self, path: Path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for name in payload.get("artifact_types", []):
            self.add_artifact_type(str(name))
        for name in payload.get("resolutions", []):
            self.add_resolution(str(name))
        for sample in payload.get("samples", []):
            raw_features = sample.get("features_json", "{}")
            try:
                features = json.loads(raw_features) if isinstance(raw_features, str) else raw_features
            except Exception:
                features = {"raw": raw_features}
            self.add_sample(
                source_path=str(sample.get("source_path","")),
                source_name=str(sample.get("source_name","Imported")),
                series_uid=str(sample.get("series_uid","")),
                series_description=str(sample.get("series_description","")),
                instance_number=int(sample.get("instance_number") or 0),
                artifact_type=str(sample.get("artifact_type","Not Artifact")),
                resolution=str(sample.get("resolution","")),
                is_normal_reference=bool(sample.get("is_normal_reference",0)),
                normal_reference_path=str(sample.get("normal_reference_path","")),
                features=features,
                notes=str(sample.get("notes","")),
            )
