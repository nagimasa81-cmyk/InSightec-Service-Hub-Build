from __future__ import annotations

"""Optional developer diagnostic for canonical module routing.

This script is intentionally not a blocking GitHub Actions gate. Production
builds are protected by contract_audit.py and preflight_check.py. Keeping the
same checks in three places created duplicate failure modes without improving
payload validation.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_manager import canonical_build_script, canonical_source_entry, load_registry
from builders.base import BaseBuilder
from common.build_common import extract_zip, latest_source_zip


def portable_relative(path: Path, base: Path) -> str:
    """Return a display-only relative path without Path.relative_to failures.

    Windows runners may expose the same temporary directory through long and
    8.3 aliases. os.path.relpath handles that display case more reliably than
    strict pathlib ancestry checks. This value is never used for trust or file
    access decisions.
    """
    try:
        return Path(os.path.relpath(str(path), str(base))).as_posix()
    except (OSError, ValueError):
        return path.name


def main() -> int:
    registry = load_registry()
    module = "Complaint_service_hub"
    config = registry["modules"][module]

    expected = {
        "source_entry_point": "launcher.py",
        "build_script": "01_BUILD_EXE_NUITKA.bat",
        "smoke_executable": "Complaint_Service_Hub_Launcher.exe",
        "main_executable": "Complaint_Service_Hub.exe",
    }
    actual = {
        "source_entry_point": canonical_source_entry(config),
        "build_script": canonical_build_script(config),
        "smoke_executable": config.get("smoke_executable"),
        "main_executable": config.get("main_executable"),
    }
    errors = [f"{key}: expected {value!r}, got {actual.get(key)!r}"
              for key, value in expected.items() if actual.get(key) != value]

    source_zip = latest_source_zip(ROOT / "Module" / module, "")
    resolved = {}
    with tempfile.TemporaryDirectory() as temp_dir:
        source_root = extract_zip(source_zip, Path(temp_dir) / "source")

        class Context:
            pass

        context = Context()
        context.source_root = source_root
        context.module = module
        context.module_config = config
        builder = BaseBuilder(context)

        try:
            source_entry = builder._fixed_file(actual["source_entry_point"], "registry SOURCE entry")
            build_script = builder._fixed_file(actual["build_script"], "registry build script")
            resolved = {
                "source_entry": portable_relative(source_entry, source_root),
                "build_script": portable_relative(build_script, source_root),
            }
        except Exception as exc:
            errors.append(f"source resolution: {type(exc).__name__}: {exc}")

    report = {
        "status": "FAIL" if errors else "PASS",
        "purpose": "optional developer diagnostic; not a CI build gate",
        "canonical": actual,
        "resolved": resolved,
        "source_zip": source_zip.name,
        "errors": errors,
        "production_gates": ["contract_audit.py", "preflight_check.py", "post-build payload validation"],
    }
    output = ROOT / "artifacts" / "route_validation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
