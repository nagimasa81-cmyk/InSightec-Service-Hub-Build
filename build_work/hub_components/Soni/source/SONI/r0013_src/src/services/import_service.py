from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


class ImportService:
    """Open treatment folders or ZIP packages in an isolated workspace."""

    def __init__(self) -> None:
        self.temp_dirs: list[Path] = []

    @staticmethod
    def _validate_member(name: str) -> None:
        normalized = name.replace("\\", "/")
        member = PurePosixPath(normalized)
        if member.is_absolute() or ".." in member.parts:
            raise ValueError(f"Unsafe ZIP entry rejected: {name}")
        if member.parts and ":" in member.parts[0]:
            raise ValueError(f"Unsafe ZIP entry rejected: {name}")

    def open(self, source: Path) -> Path:
        source = source.expanduser().resolve()
        if source.is_dir():
            return source
        if not source.is_file():
            raise FileNotFoundError(f"Source not found: {source}")
        if source.suffix.lower() != ".zip":
            raise ValueError("Select a ZIP file or folder.")

        temp = Path(tempfile.mkdtemp(prefix="SonicationReplay_"))
        try:
            with zipfile.ZipFile(source) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f"Corrupted ZIP member: {bad}")
                for info in archive.infolist():
                    self._validate_member(info.filename)
                archive.extractall(temp)
        except Exception:
            shutil.rmtree(temp, ignore_errors=True)
            raise

        self.temp_dirs.append(temp)
        return temp

    def release(self, workspace: Path | None) -> None:
        if workspace is None:
            return
        resolved = workspace.resolve()
        for temp in list(self.temp_dirs):
            if temp.resolve() == resolved:
                shutil.rmtree(temp, ignore_errors=True)
                self.temp_dirs.remove(temp)

    def cleanup(self) -> None:
        for path in self.temp_dirs:
            shutil.rmtree(path, ignore_errors=True)
        self.temp_dirs.clear()
