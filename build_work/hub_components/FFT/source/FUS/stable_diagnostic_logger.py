from __future__ import annotations

import json
import logging
import os
import platform
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


def _root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "MR_Image_Explorer"
    return Path.home() / "AppData" / "Local" / "MR_Image_Explorer"


class StableDiagnosticLogger:
    def __init__(self, version: str):
        root = _root()
        self.log_dir = root / "logs"
        self.export_dir = root / "diagnostics"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.log_dir / f"Stable_Baseline_{stamp}.log"
        self.enabled = True

        self.logger = logging.getLogger(f"MRIE.Stable.{stamp}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        handler = logging.FileHandler(self.log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        self.logger.addHandler(handler)

        self.info(
            "APPLICATION_START",
            version=version,
            python=sys.version,
            platform=platform.platform(),
            executable=sys.executable,
        )

    @staticmethod
    def array_summary(value: Any) -> dict[str, Any]:
        if value is None:
            return {"present": False}
        try:
            array = np.asarray(value)
            finite = array[np.isfinite(array)]
            return {
                "present": True,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "size": int(array.size),
                "minimum": float(finite.min()) if finite.size else None,
                "maximum": float(finite.max()) if finite.size else None,
                "mean": float(finite.mean()) if finite.size else None,
                "nonzero": int(np.count_nonzero(array)),
            }
        except Exception as exc:
            return {"present": True, "error": f"{type(exc).__name__}: {exc}"}

    def _write(self, level: int, event: str, **fields: Any) -> None:
        if not self.enabled:
            return
        self.logger.log(
            level,
            json.dumps(
                {"event": event, **fields},
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            ),
        )

    def info(self, event: str, **fields: Any) -> None:
        self._write(logging.INFO, event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._write(logging.WARNING, event, **fields)

    def exception(self, event: str, error: BaseException, **fields: Any) -> None:
        self._write(
            logging.ERROR,
            event,
            error_type=type(error).__name__,
            error=str(error),
            traceback="".join(traceback.format_exception(
                type(error),
                error,
                error.__traceback__,
            )),
            **fields,
        )

    def export_zip(self, destination: Path, state: dict[str, Any]) -> Path:
        destination = Path(destination)
        state_path = self.log_dir / "stable_display_state.json"
        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        for handler in self.logger.handlers:
            handler.flush()

        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(self.log_path, f"logs/{self.log_path.name}")
            archive.write(state_path, f"state/{state_path.name}")
        return destination
