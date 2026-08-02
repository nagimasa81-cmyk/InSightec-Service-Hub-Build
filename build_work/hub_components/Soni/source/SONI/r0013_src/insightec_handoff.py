from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "insightec.auto-analysis.handoff.v1"

@dataclass(frozen=True)
class Handoff:
    source: Path
    payload: dict[str, Any]

    @property
    def schema(self) -> str:
        return str(self.payload.get("schema") or self.payload.get("handoff_schema") or "")

    @property
    def auto_load(self) -> bool:
        return bool(self.payload.get("auto_load", True))

    @property
    def auto_analyze(self) -> bool:
        return bool(self.payload.get("auto_analyze", True))

    def workspace(self) -> Path | None:
        raw = self.payload.get("workspace_path") or self.payload.get("workspace")
        if not raw:
            return None
        p = Path(str(raw)).expanduser()
        return p.resolve() if p.exists() else None

    def input_paths(self) -> list[Path]:
        values: list[Any] = []
        for key in ("matched_files", "files", "source_paths", "inputs"):
            value = self.payload.get(key)
            if isinstance(value, list):
                values.extend(value)
            elif isinstance(value, str) and value.strip():
                values.append(value)
        primary = self.payload.get("primary_input")
        if primary:
            values.insert(0, primary)
        workspace = self.workspace()
        result: list[Path] = []
        seen: set[str] = set()
        for value in values:
            if isinstance(value, dict):
                value = value.get("path") or value.get("file")
            if not value:
                continue
            p = Path(str(value)).expanduser()
            if not p.is_absolute() and workspace:
                p = workspace / p
            try:
                p = p.resolve()
            except OSError:
                continue
            key = os.path.normcase(str(p))
            if p.exists() and key not in seen:
                seen.add(key); result.append(p)
        return result

    def preferred_source(self) -> Path | None:
        paths = self.input_paths()
        if paths:
            return paths[0]
        return self.workspace()

    def preferred_dataset_source(self) -> Path | None:
        """Return a complete Sonication dataset source, not an extracted member file.

        Hub payloads contain both the original dropped source(s) and detected
        matched files. For Sonication Replay, the original ZIP/folder must win.
        """
        workspace = self.workspace()
        values: list[Any] = []
        primary = self.payload.get("primary_input")
        if primary:
            values.append(primary)
        for key in ("source_paths", "inputs", "files"):
            value = self.payload.get(key)
            if isinstance(value, list):
                values.extend(value)
            elif isinstance(value, str) and value.strip():
                values.append(value)

        candidates: list[Path] = []
        seen: set[str] = set()
        for value in values:
            if isinstance(value, dict):
                value = value.get("path") or value.get("file")
            if not value:
                continue
            path = Path(str(value)).expanduser()
            if not path.is_absolute() and workspace:
                path = workspace / path
            try:
                path = path.resolve()
            except OSError:
                continue
            key = os.path.normcase(str(path))
            if path.exists() and key not in seen:
                seen.add(key)
                candidates.append(path)

        # A ZIP preserves the complete original package and is the best source.
        for path in candidates:
            if path.is_file() and path.suffix.lower() == ".zip":
                return path
        # A selected folder is also a complete dataset source.
        for path in candidates:
            if path.is_dir():
                return path
        # Fall back to Hub's extracted workspace, which contains the full package.
        if workspace and workspace.is_dir():
            return workspace
        # Last resort for backward compatibility.
        return self.preferred_source()

    def mark(self, tool_id: str, stage: str, **extra: Any) -> None:
        data = {"schema": SCHEMA, "tool_id": tool_id, "stage": stage, "handoff": str(self.source), **extra}
        try:
            receipt = self.source.with_name(self.source.stem + f".{tool_id}.receipt.json")
            receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass


def _handoff_argument() -> str | None:
    args = list(sys.argv)
    cleaned = [args[0]] if args else []
    found: str | None = None
    index = 1
    while index < len(args):
        arg = args[index]
        if arg == "--handoff" and index + 1 < len(args):
            found = args[index + 1]; index += 2; continue
        if arg.startswith("--handoff="):
            found = arg.split("=", 1)[1]; index += 1; continue
        cleaned.append(arg); index += 1
    sys.argv[:] = cleaned
    return found


def load_handoff(required_tool: str | None = None) -> Handoff | None:
    raw = _handoff_argument() or os.environ.get("INSIGHTEC_HANDOFF", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Handoff JSON does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("Handoff root must be a JSON object")
    schema = str(payload.get("schema") or payload.get("handoff_schema") or "")
    if schema and schema != SCHEMA:
        raise RuntimeError(f"Unsupported handoff schema: {schema}")
    tool = str(payload.get("tool") or payload.get("tool_id") or "")
    if required_tool and tool and tool.casefold() not in {required_tool.casefold(), required_tool.replace("_", " ").casefold()}:
        # Hub releases have used both display names and IDs. Treat this as metadata,
        # not a fatal mismatch, but preserve it in the receipt.
        payload["received_tool_mismatch"] = {"expected": required_tool, "received": tool}
    return Handoff(path, payload)
