from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import traceback
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = ROOT / "Module"
CACHE_ROOT = ROOT / ".rc9_cache"
OUTPUT_ROOT = ROOT / "artifacts"
PYTHON_VERSION = "3.14"
HUB_MODULE = "InSightec_Service_hub"
DEFAULT_MODULE_VERSIONS = {
    "InSightec_Service_hub": "9.0",
    "DO_Analysis": "7.4",
    "Log_explorer": "9.0",
    "trackerSNR": "2.2",
    "FFT": "8.7",
    "Soni": "1.6",
    "VIMeasure": "7.3",
}

ARTIFACT_NAMES = {
    "InSightec_Service_hub:zip_drop": "ServiceHub",
    "InSightec_Service_hub:card_launcher": "ServiceHubCard",
    "DO_Analysis": "DOAnalysis",
    "Log_explorer": "LogExplorer",
    "trackerSNR": "TrackerSNR",
    "FFT": "FUSImageExplore",
    "Soni": "Sonication",
    "VIMeasure": "VIMeasure",
}

@dataclass(frozen=True)
class Options:
    build_target: str
    module_name: str
    hub_variant: str
    hub_guide: bool
    module_guide: bool
    source_zip: str


class BuildCommandError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, log_path: Path):
        super().__init__(f"Command failed ({returncode}): {command}; log={log_path}")
        self.command = command
        self.returncode = returncode
        self.log_path = log_path


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def as_bool(value: str | bool) -> bool:
    return value if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "on"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(command: list[str], cwd: Path, log_name: str = "command.log") -> Path:
    """Run a command while preserving a complete UTF-8 build log."""
    log_dir = cwd / "rc9_diagnostics"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_name
    print("[RUN]", subprocess.list2cmdline(command), flush=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as stream:
        process = subprocess.Popen(
            command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            stream.write(line)
        returncode = process.wait()
    if returncode:
        raise BuildCommandError(command, returncode, log_path)
    return log_path


def find_modules() -> list[str]:
    if not MODULE_ROOT.is_dir():
        raise FileNotFoundError(f"Module directory missing: {MODULE_ROOT}")
    modules = sorted(p.name for p in MODULE_ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not modules:
        raise RuntimeError("No modules detected.")
    print("[PASS] Module auto detection:", ", ".join(modules))
    return modules


def select_source(module_dir: Path, requested: str) -> Path:
    if requested:
        source = module_dir / requested
        if not source.is_file() or not zipfile.is_zipfile(source):
            raise FileNotFoundError(f"Requested valid SOURCE ZIP missing: {source}")
        return source
    candidates = [p for p in module_dir.rglob("*.zip") if "source" in p.name.lower() and "artifact" not in p.name.lower() and zipfile.is_zipfile(p)]
    if not candidates:
        raise FileNotFoundError(f"No valid SOURCE ZIP in {module_dir}")
    return max(candidates, key=lambda p: p.stat().st_mtime_ns)


def safe_extract(source: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if destination != target and destination not in target.parents:
                raise ValueError(f"Unsafe ZIP path: {info.filename}")
        archive.extractall(destination)


def unwrap(root: Path) -> Path:
    current = root
    for _ in range(6):
        items = [p for p in current.iterdir() if p.name != "__MACOSX"]
        dirs = [p for p in items if p.is_dir()]
        files = [p for p in items if p.is_file()]
        if len(dirs) == 1 and not files:
            current = dirs[0]
        else:
            break
    return current


def infer_version(module_name: str, source: Path) -> str:
    match = re.search(r"(?i)RC[_-]?(\d+(?:[._]\d+)*)", source.stem)
    if match:
        return match.group(1).replace("_", ".")
    return DEFAULT_MODULE_VERSIONS.get(module_name, "")


def metadata(root: Path, module_name: str, source: Path) -> dict:
    path = root / "version.json"
    if path.is_file():
        data = load_json(path)
        version = str(data.get("version") or data.get("release") or "").strip()
        if not version:
            raise ValueError("version.json: version or release is required.")
        data["version"] = re.sub(r"(?i)^RC", "", version)
        return data

    version = infer_version(module_name, source)
    if not version:
        raise FileNotFoundError(
            f"version.json missing and version cannot be inferred: module={module_name}, source={source}"
        )
    print(f"[WARN] Legacy SOURCE has no version.json; RC9 metadata generated: module={module_name}, version={version}")
    return {
        "product": module_name,
        "version": version,
        "release": f"RC{version}",
        "commit": "legacy-migrated",
        "generated_by": "RC9 build.py",
    }


def actual_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def cache_key(source: Path, opts: Options) -> str:
    variant_key = opts.hub_variant if opts.module_name == HUB_MODULE else 'module'
    pieces = [sha256_file(source), sha256_file(Path(__file__)), actual_python_version(), str(opts.hub_guide), str(opts.module_guide), variant_key]
    return hashlib.sha256("|".join(pieces).encode()).hexdigest()


def copy_source(root: Path, stage: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "build", "dist", "release", "artifacts", ".git", ".rc9_cache")
    shutil.copytree(root, stage, ignore=ignore)


def apply_options(stage: Path, opts: Options, meta: dict) -> None:
    """Apply workflow options. For Hub builds, workflow input overrides legacy SOURCE metadata."""
    is_hub = opts.module_name == HUB_MODULE
    source_variant = str(meta.get("hub_variant", "")).strip()
    resolved_variant = opts.hub_variant if is_hub else "not_applicable"

    if not (stage / "version.json").is_file():
        write_json(stage / "version.json", meta)

    if is_hub:
        if source_variant not in {"", "card_launcher", "zip_drop"}:
            print(f"[WARN] Invalid SOURCE hub_variant={source_variant!r}; workflow value will be used.")
        elif not source_variant:
            print(f"[INFO] SOURCE has no hub_variant; workflow value applied: {resolved_variant}")
        elif source_variant != resolved_variant:
            print(f"[INFO] Hub Variant overridden by workflow: SOURCE={source_variant}, selected={resolved_variant}")
        meta["hub_variant"] = resolved_variant
        write_json(stage / "version.json", meta)

    options = {
        "schema": "rc9",
        "hub_variant": resolved_variant,
        "hub_guide_enabled": opts.hub_guide,
        "module_guide_enabled": opts.module_guide,
        "python_version": actual_python_version(),
    }
    write_json(stage / "build_options.json", options)
    config_path = stage / "config.json"
    if config_path.is_file():
        config = load_json(config_path)
        config["hub_guide_enabled"] = opts.hub_guide
        config["module_guide_enabled"] = opts.module_guide
        if is_hub:
            config["hub_variant"] = resolved_variant
        else:
            config.pop("hub_variant", None)
        config["settings_source"] = "build_options.json"
        write_json(config_path, config)
    os.environ.update({
        "INSIGHTEC_HUB_VARIANT": resolved_variant,
        "INSIGHTEC_HUB_GUIDE": "1" if opts.hub_guide else "0",
        "INSIGHTEC_MODULE_GUIDE": "1" if opts.module_guide else "0",
    })


def normalized_version(meta: dict) -> str:
    return str(meta.get("version") or meta.get("release") or "").strip()


def ensure_rc9_manifest(stage: Path, opts: Options, meta: dict) -> Path:
    """Normalize an existing manifest or generate one for legacy RC modules."""
    version = normalized_version(meta)
    if not version:
        raise ValueError("Cannot generate RC9 manifest without version.json version/release.")
    is_hub = opts.module_name == HUB_MODULE
    preferred = stage / ("hub_manifest.json" if is_hub else "manifest.json")
    existing = next((stage / name for name in ("hub_manifest.json", "manifest.json") if (stage / name).is_file()), None)
    manifest = {}
    if existing:
        try:
            manifest = load_json(existing)
        except Exception as exc:
            raise ValueError(f"Invalid existing manifest JSON: {existing.name}: {exc}") from exc
    product = str(meta.get("product") or manifest.get("product_name") or manifest.get("name") or opts.module_name)
    manifest.update({
        "manifest_schema": "rc9",
        "schema": "insightec.rc9.manifest.v1",
        "artifact_type": "service_hub" if is_hub else "module",
        "id": str(manifest.get("id") or opts.module_name),
        "name": str(manifest.get("name") or product),
        "product_name": product,
        "version": version,
        "release": str(meta.get("release") or manifest.get("release") or f"RC{version}"),
        "commit": str(meta.get("commit") or manifest.get("commit") or ""),
        "python_version": actual_python_version(),
        "hub_guide_enabled": opts.hub_guide,
        "module_guide_enabled": opts.module_guide,
    })
    if is_hub:
        manifest["hub_variant"] = opts.hub_variant
    else:
        manifest["module_id"] = opts.module_name
        manifest.pop("hub_variant", None)
    write_json(preferred, manifest)
    if existing and existing != preferred:
        existing.unlink()
    print(f"[PASS] RC9 manifest {'normalized' if existing else 'generated'}: {preferred.name}")
    return preferred

def python_syntax_check(root: Path) -> int:
    files = [p for p in root.rglob("*.py") if not any(part in {"build", "dist", ".venv", "venv"} for part in p.parts)]
    if not files:
        raise RuntimeError("No Python files found for syntax check.")
    for path in files:
        py_compile.compile(str(path), doraise=True)
    return len(files)


def install_requirements(root: Path) -> None:
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], root)
    for name in ("requirements-build.txt", "requirements.txt"):
        requirement = root / name
        if requirement.is_file():
            run([sys.executable, "-m", "pip", "install", "-r", str(requirement)], root)
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if data.get("project") or data.get("build-system"):
            run([sys.executable, "-m", "pip", "install", "."], root)
    run([sys.executable, "-m", "pip", "install", "pyinstaller", "nuitka", "ordered-set", "zstandard"], root)


def is_rc9_wrapper_bat(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig", errors="ignore").lower()
    return "scripts\\build.py" in text or "scripts/build.py" in text


def choose_spec(stage: Path, meta: dict) -> Path | None:
    requested = str(meta.get("build_spec", "")).strip()
    if requested:
        path = stage / requested
        if not path.is_file():
            raise FileNotFoundError(f"version.json build_spec missing: {requested}")
        return path
    specs = sorted(stage.glob("*.spec"))
    if len(specs) > 1:
        raise RuntimeError("Multiple SPEC files found. Set build_spec in version.json.")
    return specs[0] if specs else None


def choose_entry(stage: Path, meta: dict) -> Path | None:
    requested = str(meta.get("build_entry", "")).strip()
    if requested:
        path = stage / requested
        if not path.is_file():
            raise FileNotFoundError(f"version.json build_entry missing: {requested}")
        return path
    known = [stage / n for n in ("InSightecServiceHub.py", "main.py", "app.py") if (stage / n).is_file()]
    if len(known) > 1:
        raise RuntimeError("Multiple Python entry points found. Set build_entry in version.json.")
    if known:
        return known[0]
    pyproject = stage / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        scripts = data.get("project", {}).get("scripts", {})
        if len(scripts) == 1:
            module = next(iter(scripts.values())).split(":", 1)[0]
            candidate = stage / (module.replace(".", os.sep) + ".py")
            if candidate.is_file():
                return candidate
    return None


def collect_pyinstaller_diagnostics(stage: Path, failed_log: Path | None = None) -> dict:
    """Collect actionable diagnostics from PyInstaller/Nuitka output and warn files."""
    patterns = {
        "missing_modules": re.compile(r"(?:missing module named|ModuleNotFoundError: No module named)\s*['\"]?([^'\"\s]+)", re.I),
        "missing_dlls": re.compile(r"(?:failed to collect dynamic library|could not find|cannot find)[^\n]*?([A-Za-z0-9_.+-]+\.dll)", re.I),
        "hidden_imports": re.compile(r"hidden import ['\"]([^'\"]+)['\"] not found", re.I),
        "qt_plugins": re.compile(r"(?:qwindows\.dll|platforms[/\\]|Qt6[A-Za-z]+\.dll)", re.I),
    }
    texts: list[str] = []
    files: list[str] = []
    candidates = []
    if failed_log and failed_log.is_file():
        candidates.append(failed_log)
    candidates.extend(stage.rglob("warn-*.txt"))
    candidates.extend(stage.rglob("*.log"))
    seen: set[Path] = set()
    for path in candidates:
        try:
            path = path.resolve()
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            texts.append(text)
            files.append(str(path.relative_to(stage.resolve())) if stage.resolve() in path.parents else str(path))
        except Exception:
            continue
    joined = "\n".join(texts)
    result: dict[str, object] = {"log_files": files}
    for key, pattern in patterns.items():
        values = sorted(set(m.group(1) if m.groups() else m.group(0) for m in pattern.finditer(joined)))
        result[key] = values[:100]
    lower = joined.lower()
    classifications = []
    for token, label in (
        ("failed to collect dynamic library", "dynamic_library_collection"),
        ("modulenotfounderror", "missing_python_module"),
        ("hidden import", "hidden_import"),
        ("qwindows.dll", "qt_platform_plugin"),
        ("recursionerror", "recursion_error"),
        ("permissionerror", "permission_error"),
        ("no space left", "disk_space"),
        ("syntaxerror", "syntax_error"),
    ):
        if token in lower:
            classifications.append(label)
    result["classifications"] = classifications
    suggestions = []
    if result["missing_modules"]:
        suggestions.append("Add missing packages to requirements.txt and hidden imports to the SPEC where needed.")
    if result["missing_dlls"]:
        suggestions.append("Add the missing DLL package/runtime or collect_dynamic_libs() entry to the SPEC.")
    if "qt_platform_plugin" in classifications or result["qt_plugins"]:
        suggestions.append("Verify PySide6/Qt plugin collection, especially platforms/qwindows.dll.")
    if "dynamic_library_collection" in classifications:
        suggestions.append("Check collect_dynamic_libs()/binaries in the SPEC and architecture compatibility.")
    result["suggestions"] = suggestions
    return result


def write_build_failure_report(stage: Path, exc: Exception) -> Path:
    failed_log = exc.log_path if isinstance(exc, BuildCommandError) else None
    diagnostics = collect_pyinstaller_diagnostics(stage, failed_log)
    report = stage / "rc9_diagnostics" / "build_failure.json"
    write_json(report, {
        "schema": "rc9.build-diagnostics.v1",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "diagnostics": diagnostics,
    })
    print("[FAIL] Build diagnostics report:", report)
    for classification in diagnostics.get("classifications", []):
        print("[DIAG] classification:", classification)
    for item in diagnostics.get("missing_modules", []):
        print("[DIAG] missing module:", item)
    for item in diagnostics.get("missing_dlls", []):
        print("[DIAG] missing DLL:", item)
    for suggestion in diagnostics.get("suggestions", []):
        print("[DIAG] suggestion:", suggestion)
    return report


def validate_runtime_payload(payload: Path) -> tuple[bool, list[str]]:
    """Check common runtime files without assuming every module uses Qt."""
    problems: list[str] = []
    payload_files = [p for p in payload.rglob("*") if p.is_file()]
    files_lower = {p.name.lower() for p in payload_files}
    relative_text = " ".join(p.relative_to(payload).as_posix().lower() for p in payload_files)
    uses_qt = any(name.startswith("qt6") and name.endswith(".dll") for name in files_lower) or "pyside6" in relative_text
    if uses_qt:
        if "qwindows.dll" not in files_lower:
            problems.append("Qt payload missing platforms/qwindows.dll")
        for dll in ("qt6core.dll", "qt6gui.dll", "qt6widgets.dll"):
            if dll not in files_lower:
                problems.append(f"Qt payload missing {dll}")
    return not problems, problems


def build(stage: Path, meta: dict) -> None:
    spec = choose_spec(stage, meta)
    if spec:
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", spec.name], stage, "pyinstaller_spec.log")
        return
    requested_builder = str(meta.get("build_script", "")).strip()
    builder_candidates = ([stage / requested_builder] if requested_builder else []) + [stage / "Build_Hub_EXE.py", stage / "build.py"]
    builder = next((p for p in builder_candidates if p.is_file() and p.resolve() != Path(__file__).resolve()), None)
    if builder:
        run([sys.executable, builder.name], stage, "builder_script.log")
        return
    bats = [stage / n for n in ("01_BUILD_EXE_NUITKA.bat", "BUILD_EXE_NUITKA.bat", "BUILD_EXE.bat", "build.bat", "01_BUILD_EXE.bat")]
    bat = next((p for p in bats if p.is_file() and not is_rc9_wrapper_bat(p)), None)
    if bat and os.name == "nt":
        run(["cmd.exe", "/d", "/c", bat.name], stage, "builder_bat.log")
        return
    entry = choose_entry(stage, meta)
    if not entry:
        raise RuntimeError("No unambiguous SPEC, builder, usable BAT, pyproject entry, or Python entry point.")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", entry.stem, str(entry.relative_to(stage))], stage, "pyinstaller_entry.log")


def find_distribution(stage: Path) -> tuple[Path, Path]:
    dist_root = stage / "dist"
    if not dist_root.is_dir():
        raise RuntimeError("dist generation check failed.")
    exes = [p for p in dist_root.rglob("*.exe") if p.is_file()]
    if not exes:
        raise RuntimeError("EXE generation check failed inside dist.")
    if len(exes) > 1:
        top = [p for p in exes if p.parent.parent == dist_root or p.parent == dist_root]
        exes = top or exes
    exe = max(exes, key=lambda p: p.stat().st_mtime_ns)
    payload = exe.parent if exe.parent != dist_root else dist_root
    return payload, exe


def artifact_name(module: str, variant: str, version: str, guide: bool) -> str:
    """Return the GitHub Artifact name. GitHub itself adds the outer ZIP on download."""
    key = f"{module}:{variant}" if module == HUB_MODULE else module
    base = ARTIFACT_NAMES.get(key, re.sub(r"[^A-Za-z0-9]", "", module))
    clean = re.sub(r"(?i)^RC", "", str(version)).strip()
    return f"{base}_RC{clean}{'G' if guide else ''}"


def classify_payload_zip(relative: Path, meta: dict | None = None) -> tuple[bool, str]:
    """Classify ZIP files embedded in a built payload.

    GitHub upload-artifact always creates the outer download ZIP. RC9 therefore
    forbids product/distribution ZIP wrappers inside the uploaded directory, but
    permits runtime ZIPs that are required by frozen Python applications, such as
    PyInstaller's _internal/base_library.zip. Additional intentional ZIP resources
    can be explicitly whitelisted with version.json -> allowed_payload_zips.
    """
    normalized = relative.as_posix().lstrip("./")
    lower_name = relative.name.lower()
    lower_parts = {part.lower() for part in relative.parts}
    if lower_name == "base_library.zip" and ("_internal" in lower_parts or len(relative.parts) == 1):
        return True, "PyInstaller runtime library"
    if lower_name.startswith("python") and lower_name.endswith(".zip") and "_internal" in lower_parts:
        return True, "Frozen Python runtime library"
    allowed = []
    if isinstance(meta, dict):
        value = meta.get("allowed_payload_zips", [])
        if isinstance(value, list):
            allowed = [str(item).replace("\\", "/").lstrip("./") for item in value]
    if normalized in allowed:
        return True, "Explicitly allowed by version.json"
    return False, "Distribution/resource ZIP is not allowed in the Artifact payload"


def payload_zip_inventory(root: Path, meta: dict | None = None) -> list[dict[str, object]]:
    inventory: list[dict[str, object]] = []
    if not root.is_dir():
        return inventory
    for path in sorted(root.rglob("*.zip")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        allowed, reason = classify_payload_zip(relative, meta)
        inventory.append({"path": relative.as_posix(), "allowed": allowed, "reason": reason})
    return inventory


def prepare_package(payload: Path, package_dir: Path, stage: Path, meta: dict) -> None:
    """Create the directory uploaded by actions/upload-artifact.

    Do not create a distributable ZIP here. upload-artifact produces the one and only
    downloaded ZIP. This prevents GitHub Artifact ZIP -> product/distribution ZIP nesting while preserving required runtime ZIPs.
    """
    shutil.rmtree(package_dir, ignore_errors=True)
    package_dir.mkdir(parents=True, exist_ok=True)
    inventory = payload_zip_inventory(payload, meta)
    forbidden = [item for item in inventory if not item["allowed"]]
    for item in inventory:
        status = "ALLOW" if item["allowed"] else "FORBID"
        print(f"[{status}] Payload ZIP: {item['path']} ({item['reason']})")
    if forbidden:
        details = " | ".join(f"{item['path']}: {item['reason']}" for item in forbidden)
        raise RuntimeError("Forbidden ZIP detected in build payload: " + details)
    for path in sorted(payload.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(payload)
        target = package_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    for name in ("version.json", "build_options.json", "hub_manifest.json", "manifest.json"):
        source = stage / name
        target = package_dir / name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)
    write_json(package_dir / "payload_zip_inventory.json", {
        "schema": "rc9.payload_zip_inventory.v1",
        "outer_archive_created_by": "actions/upload-artifact",
        "entries": inventory,
        "forbidden_count": len(forbidden),
    })


def make_verification_zip(package_dir: Path, output: Path) -> None:
    """Create a temporary ZIP only for Triple Check; it is never uploaded."""
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package_dir))


def validate_manifest_data(manifest: dict, opts: Options, meta: dict) -> bool:
    version = normalized_version(meta)
    if manifest.get("manifest_schema") != "rc9":
        return False
    if manifest.get("schema") != "insightec.rc9.manifest.v1":
        return False
    if str(manifest.get("version", "")) != version:
        return False
    if opts.module_name == HUB_MODULE:
        return manifest.get("artifact_type") == "service_hub" and manifest.get("hub_variant") == opts.hub_variant
    return (manifest.get("artifact_type") == "module" and
            manifest.get("module_id") == opts.module_name and
            bool(manifest.get("id") or manifest.get("name")) and
            "hub_variant" not in manifest)


def validate_manifest(stage: Path, opts: Options, meta: dict) -> bool:
    expected = stage / ("hub_manifest.json" if opts.module_name == HUB_MODULE else "manifest.json")
    if not expected.is_file():
        return False
    try:
        return validate_manifest_data(load_json(expected), opts, meta)
    except Exception:
        return False


def inspect_package(package_dir: Path, opts: Options | None = None, meta: dict | None = None) -> tuple[bool, bool, bool, bool, bool]:
    if not package_dir.is_dir():
        return False, False, False, False, False
    files = [p for p in package_dir.rglob("*") if p.is_file()]
    safe = bool(files) and all(package_dir.resolve() in p.resolve().parents for p in files)
    effective_meta = meta
    if effective_meta is None and (package_dir / "version.json").is_file():
        try:
            effective_meta = load_json(package_dir / "version.json")
        except Exception:
            effective_meta = None
    zip_inventory = payload_zip_inventory(package_dir, effective_meta)
    no_double = all(bool(item["allowed"]) for item in zip_inventory)
    has_exe = any(p.suffix.lower() == ".exe" for p in files)
    has_options = (package_dir / "build_options.json").is_file()
    manifest_name = "hub_manifest.json" if opts and opts.module_name == HUB_MODULE else "manifest.json"
    manifest_ok = False
    manifest_path = package_dir / manifest_name
    if opts and meta and manifest_path.is_file():
        try:
            manifest_ok = validate_manifest_data(load_json(manifest_path), opts, meta)
        except Exception:
            manifest_ok = False
    return safe, no_double, has_exe, has_options, manifest_ok


def inspect_verification_zip(archive_path: Path, opts: Options, meta: dict) -> tuple[bool, bool, bool, bool, bool]:
    if not archive_path.is_file() or not zipfile.is_zipfile(archive_path):
        return False, False, False, False, False
    with zipfile.ZipFile(archive_path) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        safe = bool(names) and all(n and not n.startswith(("/", "\\")) and ".." not in Path(n).parts for n in names)
        zip_names = [Path(n) for n in names if n.lower().endswith(".zip")]
        no_double = all(classify_payload_zip(name, meta)[0] for name in zip_names)
        has_exe = any(n.lower().endswith(".exe") for n in names)
        has_options = "build_options.json" in names
        manifest_name = "hub_manifest.json" if opts.module_name == HUB_MODULE else "manifest.json"
        manifest_ok = False
        if manifest_name in names:
            try:
                manifest_ok = validate_manifest_data(json.loads(archive.read(manifest_name).decode("utf-8-sig")), opts, meta)
            except Exception:
                manifest_ok = False
    return safe, no_double, has_exe, has_options, manifest_ok


def startup_smoke_test(exe: Path, timeout_seconds: int = 12) -> tuple[bool, str]:
    """Detect immediate PyInstaller/Nuitka startup crashes before publishing an artifact."""
    if os.name != "nt":
        return True, "Skipped outside Windows"
    env_map = os.environ.copy()
    env_map["INSIGHTEC_BUILD_SMOKE_TEST"] = "1"
    try:
        process = subprocess.Popen(
            [str(exe)], cwd=exe.parent, env=env_map,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            code = process.returncode
            detail = (stderr or stdout or b"").decode("utf-8", errors="replace").strip()
            if code == 0:
                return True, detail or "Process exited normally"
            return False, detail or f"Process exited immediately with code {code}"
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return True, f"Process remained running for {timeout_seconds}s"
    except Exception as exc:
        return False, f"Unable to launch EXE: {exc}"


def run_triple_check(stage: Path, payload: Path, exe: Path, package_dir: Path,
                     opts: Options, meta: dict) -> tuple[dict[str, bool], str]:
    p_safe, p_no_double, p_has_exe, p_has_options, p_manifest = inspect_package(package_dir, opts, meta)
    options = load_json(stage / "build_options.json")
    smoke_ok, smoke_detail = startup_smoke_test(exe)
    runtime_ok, runtime_problems = validate_runtime_payload(payload)
    if runtime_problems:
        smoke_detail = smoke_detail + " | " + " | ".join(runtime_problems)
    checks = {
        "version.json": (stage / "version.json").is_file() and bool(meta.get("version")),
        "manifest": validate_manifest(stage, opts, meta) and p_manifest,
        "Module": opts.module_name in find_modules(),
        "Package structure": p_safe and p_has_exe and p_has_options,
        "BAT": any(stage.rglob("*.bat")),
        "SPEC/build definition": bool(any(stage.rglob("*.spec")) or any(stage.rglob("Build_*EXE.py")) or (stage / "pyproject.toml").is_file() or choose_entry(stage, meta)),
        "Python syntax": python_syntax_check(stage) >= 1,
        "dist generated": payload.is_dir() and any(payload.iterdir()),
        "EXE generated": exe.is_file() and exe.stat().st_size > 0,
        "Runtime dependency payload": runtime_ok,
        "EXE startup smoke test": smoke_ok,
        "Artifact payload generated": package_dir.is_dir() and any(package_dir.iterdir()),
        "No distribution ZIP wrapper": p_no_double,
        "Hub Variant": opts.module_name != HUB_MODULE or meta.get("hub_variant") == opts.hub_variant,
        "Guide settings": options.get("hub_guide_enabled") == opts.hub_guide and options.get("module_guide_enabled") == opts.module_guide and p_has_options,
        "Python version": actual_python_version() == PYTHON_VERSION,
    }
    return checks, smoke_detail


def directory_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "triple_check.json"):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def write_report(path: Path, checks: dict[str, bool], key: str, source: Path,
                 artifact_name_value: str, package_dir: Path, opts: Options, smoke_detail: str) -> None:
    write_json(path, {
        "schema": "rc9",
        "result": "PASS" if all(checks.values()) else "FAIL",
        "cache_key": key,
        "source_sha256": sha256_file(source),
        "build_py_sha256": sha256_file(Path(__file__)),
        "artifact": artifact_name_value,
        "artifact_payload_sha256": directory_sha256(package_dir),
        "python_version": actual_python_version(),
        "hub_variant": opts.hub_variant if opts.module_name == HUB_MODULE else "not_applicable",
        "hub_guide_enabled": opts.hub_guide,
        "module_guide_enabled": opts.module_guide,
        "startup_smoke_test_detail": smoke_detail,
        "checks": checks,
    })


def save_cache(cache_dir: Path, package_dir: Path, report: Path) -> bool:
    shutil.rmtree(cache_dir, ignore_errors=True)
    cached_package = cache_dir / "package"
    cached_package.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_dir, cached_package)
    shutil.copy2(report, cache_dir / "triple_check.json")
    return directory_sha256(cached_package) == directory_sha256(package_dir)


def restore_cache(cache_dir: Path, key: str, source: Path, opts: Options) -> bool:
    report_path = cache_dir / "triple_check.json"
    cached_package = cache_dir / "package"
    if not report_path.is_file() or not cached_package.is_dir():
        return False
    try:
        report = load_json(report_path)
        safe, no_double, has_exe, has_options, _ = inspect_package(cached_package)
        valid = all([
            report.get("result") == "PASS",
            report.get("cache_key") == key,
            report.get("source_sha256") == sha256_file(source),
            report.get("build_py_sha256") == sha256_file(Path(__file__)),
            report.get("artifact_payload_sha256") == directory_sha256(cached_package),
            report.get("python_version") == actual_python_version(),
            report.get("hub_variant") == (opts.hub_variant if opts.module_name == HUB_MODULE else "not_applicable"),
            report.get("hub_guide_enabled") == opts.hub_guide,
            report.get("module_guide_enabled") == opts.module_guide,
            safe, no_double, has_exe, has_options,
            all(report.get("checks", {}).values()),
        ])
    except Exception as exc:
        print("[WARN] Cache validation failed:", exc)
        return False
    if not valid:
        return False
    artifact_name_value = str(report["artifact"])
    output_package = OUTPUT_ROOT / artifact_name_value
    shutil.copytree(cached_package, output_package)
    shutil.copy2(report_path, output_package / "triple_check.json")
    publish_github_outputs(artifact_name_value, output_package)
    print("[PASS] Cache restored:", artifact_name_value)
    return True


def prune_cache(limit: int = 20) -> None:
    if not CACHE_ROOT.is_dir():
        return
    dirs = sorted((p for p in CACHE_ROOT.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for old in dirs[limit:]:
        shutil.rmtree(old, ignore_errors=True)


def publish_github_outputs(name: str, package_dir: Path) -> None:
    output_file = env("GITHUB_OUTPUT")
    if output_file:
        with Path(output_file).open("a", encoding="utf-8") as stream:
            stream.write(f"artifact_name={name}\n")
            stream.write(f"artifact_path={package_dir.resolve()}\n")
    print("[INFO] GitHub Artifact name:", name)
    print("[INFO] GitHub Artifact payload:", package_dir)



def inspect_source_zip_for_rc9(module_name: str, source: Path) -> tuple[bool, str]:
    """Static audit used for every SOURCE ZIP present in Module folders."""
    try:
        with tempfile.TemporaryDirectory(prefix="rc9_audit_") as temp:
            root = Path(temp) / "extract"
            root.mkdir()
            safe_extract(source, root)
            root = unwrap(root)
            version = root / "version.json"
            if version.is_file():
                meta = load_json(version)
                if not (meta.get("version") or meta.get("release")):
                    return False, "version/release missing in version.json"
                metadata_detail = "version.json present"
            else:
                inferred = infer_version(module_name, source)
                if not inferred:
                    return False, "version.json missing and no version can be inferred"
                meta = {"version": inferred}
                metadata_detail = f"legacy metadata will be generated (version={inferred})"
            definitions = list(root.rglob("*.spec")) + list(root.rglob("Build_*EXE.py"))
            entry = choose_entry(root, meta)
            if not definitions and not (root / "pyproject.toml").is_file() and not entry:
                return False, "SPEC/build definition missing"
            py_files = [p for p in root.rglob("*.py") if not any(part in {"build", "dist", "release", "__pycache__"} for part in p.parts)]
            for path in py_files:
                py_compile.compile(str(path), doraise=True)
            nested = [p for p in root.rglob("*.zip") if p.is_file()]
            if nested:
                return False, "nested ZIP in SOURCE: " + ", ".join(p.name for p in nested[:3])
            return True, f"PASS; {metadata_detail}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def audit_repository_sources(opts: Options) -> None:
    """Audit only the scope relevant to this run.

    Module builds audit the selected module only. Service Hub builds audit the Hub
    and every module that currently contains a SOURCE ZIP.
    """
    if opts.module_name == HUB_MODULE:
        audit_modules = find_modules()
        scope_label = "Service Hub + all available modules"
    else:
        audit_modules = [opts.module_name]
        scope_label = f"selected module only: {opts.module_name}"

    print(f"[INFO] Repository audit scope: {scope_label}")
    failures: list[str] = []
    warnings: list[str] = []
    checked = 0
    for module in audit_modules:
        module_dir = MODULE_ROOT / module
        if not module_dir.is_dir():
            failures.append(f"{module_dir}: module directory missing")
            continue
        sources = [p for p in module_dir.rglob("*.zip") if "source" in p.name.lower() and zipfile.is_zipfile(p)]
        if not sources:
            message = f"{module_dir.relative_to(ROOT)}: no SOURCE ZIP present"
            print(f"[SKIP] {message}")
            warnings.append(message)
            continue
        for source in sources:
            checked += 1
            ok, detail = inspect_source_zip_for_rc9(module, source)
            relative = source.relative_to(ROOT)
            print(f"[{'PASS' if ok else 'FAIL'}] Repository audit: {relative}: {detail}")
            if not ok:
                failures.append(f"{relative}: {detail}")

    print("[INFO] Repository audit summary:")
    print(f"       scope={scope_label}")
    print(f"       checked_source_zips={checked}")
    print(f"       skipped_or_warning={len(warnings)}")
    print(f"       failures={len(failures)}")
    if failures:
        print("[FAIL] Modules requiring correction:")
        for item in failures:
            print("       -", item)
        raise RuntimeError("Repository SOURCE audit failed: " + " | ".join(failures))


def parse_args() -> Options:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-target", default=env("INPUT_BUILD_TARGET", "Service Hub"))
    parser.add_argument("--module-name", default=env("INPUT_MODULE_NAME", HUB_MODULE))
    parser.add_argument("--hub-variant", default=env("INPUT_HUB_VARIANT", "card_launcher"))
    parser.add_argument("--hub-guide", default=env("INPUT_HUB_GUIDE", "false"))
    parser.add_argument("--module-guide", default=env("INPUT_MODULE_GUIDE", "false"))
    parser.add_argument("--source-zip", default=env("INPUT_SOURCE_ZIP", ""))
    args = parser.parse_args()
    module = HUB_MODULE if args.build_target in {"service_hub", "Service Hub"} else args.module_name.strip()
    if not module:
        raise ValueError("Module name is required when Build Target is Module.")
    if args.hub_variant not in {"card_launcher", "zip_drop"}:
        raise ValueError("Invalid Hub Variant.")
    if actual_python_version() != PYTHON_VERSION:
        raise RuntimeError(f"RC9 requires Python {PYTHON_VERSION}; active={actual_python_version()}")
    return Options(args.build_target, module, args.hub_variant, as_bool(args.hub_guide), as_bool(args.module_guide), args.source_zip)


def main() -> int:
    opts = parse_args()
    modules = find_modules()
    audit_repository_sources(opts)
    if opts.module_name not in modules:
        raise ValueError(f"Unknown module: {opts.module_name}. Detected: {', '.join(modules)}")
    source = select_source(MODULE_ROOT / opts.module_name, opts.source_zip)
    key = cache_key(source, opts)
    cache_dir = CACHE_ROOT / key
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
    OUTPUT_ROOT.mkdir(parents=True)
    CACHE_ROOT.mkdir(exist_ok=True)
    prune_cache()
    print("[INFO] SOURCE:", source)
    print("[INFO] Cache Key:", key)
    if restore_cache(cache_dir, key, source, opts):
        return 0
    with tempfile.TemporaryDirectory(prefix="rc9_") as temp:
        extract = Path(temp) / "extract"
        extract.mkdir()
        safe_extract(source, extract)
        root = unwrap(extract)
        meta = metadata(root, opts.module_name, source)
        stage = Path(temp) / "stage"
        copy_source(root, stage)
        apply_options(stage, opts, meta)
        ensure_rc9_manifest(stage, opts, meta)
        install_requirements(stage)
        try:
            build(stage, meta)
        except Exception as exc:
            report = write_build_failure_report(stage, exc)
            diagnostic_out = OUTPUT_ROOT / f"BUILD_FAILURE_{opts.module_name}"
            shutil.rmtree(diagnostic_out, ignore_errors=True)
            shutil.copytree(report.parent, diagnostic_out)
            publish_github_outputs(f"BUILD_FAILURE_{opts.module_name}", diagnostic_out)
            raise
        payload, exe = find_distribution(stage)
        guide = opts.hub_guide if opts.module_name == HUB_MODULE else opts.module_guide
        name = artifact_name(opts.module_name, opts.hub_variant, str(meta["version"]), guide)
        package_dir = OUTPUT_ROOT / name
        prepare_package(payload, package_dir, stage, meta)
        checks, smoke_detail = run_triple_check(stage, payload, exe, package_dir, opts, meta)
        for check_name, ok in checks.items():
            print(f"[{'PASS' if ok else 'FAIL'}] {check_name}")
        print("[INFO] EXE startup smoke test:", smoke_detail)
        failed = [check_name for check_name, ok in checks.items() if ok is not True]
        if failed:
            shutil.rmtree(package_dir, ignore_errors=True)
            raise RuntimeError("Triple Check failed before Artifact publication: " + ", ".join(failed))
        report = package_dir / "triple_check.json"
        write_report(report, checks, key, source, name, package_dir, opts, smoke_detail)
        checks["Cache"] = save_cache(cache_dir, package_dir, report)
        if not checks["Cache"]:
            shutil.rmtree(package_dir, ignore_errors=True)
            raise RuntimeError("Triple Check failed: Cache")
        write_report(report, checks, key, source, name, package_dir, opts, smoke_detail)
        shutil.copy2(report, cache_dir / "triple_check.json")
        publish_github_outputs(name, package_dir)
        print("[PASS] Cache")
        print("[PASS] Artifact payload:", package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
