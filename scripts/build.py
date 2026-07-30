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
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = ROOT / "Module"
CACHE_ROOT = ROOT / ".rc9_cache"
OUTPUT_ROOT = ROOT / "artifacts"
SUPPORTED_PYTHON = {"3.13", "3.14"}
HUB_MODULE = "InSightec_Service_hub"
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
    python_version: str
    source_zip: str


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def as_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


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


def run(command: list[str], cwd: Path) -> None:
    print("[RUN]", subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode:
        raise RuntimeError(f"Command failed ({completed.returncode}): {command}")


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
        if not source.is_file():
            raise FileNotFoundError(f"Requested SOURCE ZIP missing: {source}")
        if not zipfile.is_zipfile(source):
            raise ValueError(f"Requested file is not a valid ZIP: {source}")
        return source
    candidates = [
        p for p in module_dir.rglob("*.zip")
        if "source" in p.name.lower() and "artifact" not in p.name.lower() and zipfile.is_zipfile(p)
    ]
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
        directories = [p for p in items if p.is_dir()]
        files = [p for p in items if p.is_file()]
        if len(directories) == 1 and not files:
            current = directories[0]
        else:
            break
    return current


def metadata(root: Path) -> tuple[dict, Path]:
    version_path = root / "version.json"
    if not version_path.is_file():
        raise FileNotFoundError("version.json is required by RC9.")
    data = load_json(version_path)
    if not data.get("version"):
        raise ValueError("version.json: version is required.")
    return data, version_path


def cache_key(source: Path, opts: Options) -> str:
    pieces = [
        sha256_file(source),
        sha256_file(Path(__file__)),
        opts.python_version,
        str(opts.hub_guide),
        str(opts.module_guide),
        opts.hub_variant,
    ]
    return hashlib.sha256("|".join(pieces).encode()).hexdigest()


def copy_source(root: Path, stage: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "build", "dist", "release", "artifacts", ".git", ".rc9_cache")
    shutil.copytree(root, stage, ignore=ignore)


def apply_options(stage: Path, opts: Options, meta: dict) -> None:
    actual = str(meta.get("hub_variant", "")).strip()
    if opts.module_name == HUB_MODULE:
        if actual not in {"card_launcher", "zip_drop"}:
            raise ValueError("Hub version.json must define hub_variant=card_launcher or zip_drop.")
        if actual != opts.hub_variant:
            raise ValueError(f"Hub Variant mismatch: SOURCE={actual}, selected={opts.hub_variant}")
    write_json(stage / "build_options.json", {
        "schema": "rc9",
        "hub_variant": actual or opts.hub_variant,
        "hub_guide_enabled": opts.hub_guide,
        "module_guide_enabled": opts.module_guide,
        "python_version": opts.python_version,
    })
    os.environ.update({
        "INSIGHTEC_HUB_VARIANT": actual or opts.hub_variant,
        "INSIGHTEC_HUB_GUIDE": "1" if opts.hub_guide else "0",
        "INSIGHTEC_MODULE_GUIDE": "1" if opts.module_guide else "0",
    })


def python_syntax_check(root: Path) -> int:
    files = [
        p for p in root.rglob("*.py")
        if not any(part in {"build", "dist", ".venv", "venv"} for part in p.parts)
    ]
    if not files:
        raise RuntimeError("No Python files found for syntax check.")
    for path in files:
        py_compile.compile(str(path), doraise=True)
    return len(files)


def install_requirements(root: Path) -> None:
    requirement = next(
        (root / name for name in ("requirements-build.txt", "requirements.txt") if (root / name).is_file()),
        None,
    )
    if requirement:
        run([sys.executable, "-m", "pip", "install", "-r", str(requirement)], root)


def is_rc9_wrapper_bat(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore").lower()
    except OSError:
        return False
    return "scripts\\build.py" in text or "scripts/build.py" in text


def build(stage: Path) -> None:
    # Prefer a SPEC or dedicated Python builder. RC9 wrapper BAT files call the
    # repository-level scripts/build.py and must never be run from an extracted module.
    specs = sorted(stage.glob("*.spec"))
    if specs:
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", specs[0].name], stage)
        return

    builders = [stage / "Build_Hub_EXE.py", stage / "build.py"]
    builder = next((p for p in builders if p.is_file() and p.resolve() != Path(__file__).resolve()), None)
    if builder:
        run([sys.executable, builder.name], stage)
        return

    bat_names = ["01_BUILD_EXE_NUITKA.bat", "BUILD_EXE_NUITKA.bat", "BUILD_EXE.bat", "build.bat", "01_BUILD_EXE.bat"]
    bat = next((stage / name for name in bat_names if (stage / name).is_file() and not is_rc9_wrapper_bat(stage / name)), None)
    if bat and os.name == "nt":
        run(["cmd.exe", "/d", "/c", bat.name], stage)
        return

    entries = [stage / name for name in ("InSightecServiceHub.py", "main.py", "app.py") if (stage / name).is_file()]
    if not entries:
        raise RuntimeError("No SPEC, builder, usable BAT, or Python entry point.")
    run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", entries[0].stem, entries[0].name,
    ], stage)


def find_distribution(stage: Path) -> tuple[Path, Path]:
    exes = [p for p in stage.rglob("*.exe") if not any(part in {"venv", ".venv"} for part in p.parts)]
    if not exes:
        raise RuntimeError("EXE generation check failed.")
    exe = max(exes, key=lambda p: p.stat().st_mtime_ns)
    dist = next((p for p in exe.parents if p.name.lower() == "dist"), exe.parent)
    payload = exe.parent if exe.parent != dist else dist
    return payload, exe


def artifact_filename(module: str, variant: str, version: str, guide: bool) -> str:
    key = f"{module}:{variant}" if module == HUB_MODULE else module
    base = ARTIFACT_NAMES.get(key, re.sub(r"[^A-Za-z0-9]", "", module))
    clean = re.sub(r"(?i)^RC", "", str(version)).strip()
    suffix = "G" if guide else ""
    return f"{base}_RC{clean}{suffix}.zip"


def make_zip(payload: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".zip.tmp")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(payload.rglob("*")):
            if path.is_file() and path.suffix.lower() != ".zip":
                archive.write(path, path.relative_to(payload))
    temporary.replace(output)


def validate_manifest(stage: Path, opts: Options, meta: dict) -> bool:
    manifest_path = next((stage / name for name in ("hub_manifest.json", "manifest.json") if (stage / name).is_file()), None)
    if manifest_path is None:
        return False
    try:
        manifest = load_json(manifest_path)
    except Exception:
        return False
    if opts.module_name == HUB_MODULE:
        return (
            manifest.get("manifest_schema") == "rc9"
            and manifest.get("hub_variant") == opts.hub_variant
            and str(manifest.get("version")) == str(meta.get("version"))
        )
    return bool(manifest.get("version") or manifest.get("id") or manifest.get("name"))


def inspect_artifact(artifact: Path) -> tuple[bool, bool, bool]:
    if not artifact.is_file() or artifact.stat().st_size == 0 or not zipfile.is_zipfile(artifact):
        return False, False, False
    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
        safe = all(
            name and not name.startswith(("/", "\\")) and ".." not in Path(name).parts
            for name in names
        )
        no_double_zip = not any(name.lower().endswith(".zip") for name in names)
        has_exe = any(name.lower().endswith(".exe") for name in names)
    return safe, no_double_zip, has_exe


def run_triple_check(stage: Path, payload: Path, exe: Path, artifact: Path, opts: Options, meta: dict) -> dict[str, bool]:
    safe_zip, no_double_zip, artifact_has_exe = inspect_artifact(artifact)
    options = load_json(stage / "build_options.json")
    checks = {
        "version.json": (stage / "version.json").is_file() and bool(meta.get("version")),
        "manifest": validate_manifest(stage, opts, meta),
        "Module": opts.module_name in find_modules(),
        "ZIP structure": safe_zip and artifact_has_exe,
        "BAT": any(stage.rglob("*.bat")),
        "SPEC": any(stage.rglob("*.spec")) or any(stage.rglob("Build_*EXE.py")),
        "Python syntax": False,
        "dist generated": payload.is_dir() and any(payload.iterdir()),
        "EXE generated": exe.is_file() and exe.stat().st_size > 0,
        "Artifact generated": artifact.is_file() and artifact.stat().st_size > 0,
        "No double ZIP": no_double_zip,
        "Hub Variant": opts.module_name != HUB_MODULE or meta.get("hub_variant") == opts.hub_variant,
        "Guide settings": (
            options.get("hub_guide_enabled") == opts.hub_guide
            and options.get("module_guide_enabled") == opts.module_guide
        ),
    }
    try:
        checks["Python syntax"] = python_syntax_check(stage) >= 1
    except Exception:
        checks["Python syntax"] = False
    return checks


def verify_and_save_cache(cache_dir: Path, artifact: Path) -> bool:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_artifact = cache_dir / artifact.name
    shutil.copy2(artifact, cached_artifact)
    return cached_artifact.is_file() and sha256_file(cached_artifact) == sha256_file(artifact)


def write_report(report_path: Path, checks: dict[str, bool], key: str, source: Path, artifact: Path, opts: Options) -> None:
    write_json(report_path, {
        "schema": "rc9",
        "result": "PASS" if all(checks.values()) else "FAIL",
        "cache_key": key,
        "source_sha256": sha256_file(source),
        "build_py_sha256": sha256_file(Path(__file__)),
        "artifact": artifact.name,
        "artifact_sha256": sha256_file(artifact) if artifact.is_file() else "",
        "python_version": opts.python_version,
        "hub_variant": opts.hub_variant,
        "hub_guide_enabled": opts.hub_guide,
        "module_guide_enabled": opts.module_guide,
        "checks": checks,
    })


def restore_cache(cache_dir: Path, output_dir: Path, key: str, source: Path, opts: Options) -> bool:
    reports = sorted(cache_dir.glob("*.triple_check.json")) if cache_dir.is_dir() else []
    if not reports:
        return False
    try:
        report = load_json(reports[-1])
        artifact = cache_dir / str(report["artifact"])
        safe_zip, no_double_zip, has_exe = inspect_artifact(artifact)
        valid = all([
            report.get("result") == "PASS",
            report.get("cache_key") == key,
            report.get("source_sha256") == sha256_file(source),
            report.get("build_py_sha256") == sha256_file(Path(__file__)),
            report.get("artifact_sha256") == sha256_file(artifact),
            report.get("python_version") == opts.python_version,
            report.get("hub_variant") == opts.hub_variant,
            report.get("hub_guide_enabled") == opts.hub_guide,
            report.get("module_guide_enabled") == opts.module_guide,
            safe_zip, no_double_zip, has_exe,
            all(report.get("checks", {}).values()),
        ])
    except Exception as exc:
        print("[WARN] Cache validation failed:", exc)
        return False
    if not valid:
        print("[WARN] Cache entry rejected; rebuilding.")
        return False
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, output_dir / artifact.name)
    shutil.copy2(reports[-1], output_dir / reports[-1].name)
    for name, ok in report["checks"].items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name} (cached build)")
    print("[PASS] Cache")
    print("[PASS] Cache restored:", artifact.name)
    return True


def print_checks(checks: dict[str, bool]) -> None:
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("Triple Check failed: " + ", ".join(failed))


def parse_args() -> Options:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-target", default=env("INPUT_BUILD_TARGET", "service_hub"))
    parser.add_argument("--module-name", default=env("INPUT_MODULE_NAME", HUB_MODULE))
    parser.add_argument("--hub-variant", default=env("INPUT_HUB_VARIANT", "card_launcher"))
    parser.add_argument("--hub-guide", default=env("INPUT_HUB_GUIDE", "false"))
    parser.add_argument("--module-guide", default=env("INPUT_MODULE_GUIDE", "false"))
    parser.add_argument("--python-version", default=env("INPUT_PYTHON_VERSION", f"{sys.version_info.major}.{sys.version_info.minor}"))
    parser.add_argument("--source-zip", default=env("INPUT_SOURCE_ZIP", ""))
    args = parser.parse_args()
    module = HUB_MODULE if args.build_target in {"service_hub", "Service Hub"} else args.module_name
    opts = Options(
        args.build_target, module, args.hub_variant, as_bool(args.hub_guide),
        as_bool(args.module_guide), args.python_version, args.source_zip,
    )
    if opts.python_version not in SUPPORTED_PYTHON:
        raise ValueError("Python Version must be 3.13 or 3.14.")
    if opts.hub_variant not in {"card_launcher", "zip_drop"}:
        raise ValueError("Hub Variant must be card_launcher or zip_drop.")
    return opts


def main() -> int:
    opts = parse_args()
    modules = find_modules()
    if opts.module_name not in modules:
        raise ValueError(f"Unknown module: {opts.module_name}")

    source = select_source(MODULE_ROOT / opts.module_name, opts.source_zip)
    key = cache_key(source, opts)
    cache_dir = CACHE_ROOT / key
    OUTPUT_ROOT.mkdir(exist_ok=True)
    CACHE_ROOT.mkdir(exist_ok=True)
    print("[INFO] SOURCE:", source)
    print("[INFO] Cache Key:", key)

    if restore_cache(cache_dir, OUTPUT_ROOT, key, source, opts):
        return 0

    with tempfile.TemporaryDirectory(prefix="rc9_") as temp_dir:
        extract = Path(temp_dir) / "extract"
        extract.mkdir()
        safe_extract(source, extract)
        root = unwrap(extract)
        meta, _ = metadata(root)
        stage = Path(temp_dir) / "stage"
        copy_source(root, stage)
        apply_options(stage, opts, meta)
        print("[PASS] version.json:", meta.get("version"))

        install_requirements(stage)
        build(stage)
        payload, exe = find_distribution(stage)
        guide = opts.hub_guide if opts.module_name == HUB_MODULE else opts.module_guide
        name = artifact_filename(opts.module_name, opts.hub_variant, str(meta["version"]), guide)
        artifact = OUTPUT_ROOT / name
        make_zip(payload, artifact)

        checks = run_triple_check(stage, payload, exe, artifact, opts, meta)
        checks["Cache"] = verify_and_save_cache(cache_dir, artifact)
        print_checks(checks)

        report = artifact.with_suffix(".triple_check.json")
        write_report(report, checks, key, source, artifact, opts)
        shutil.copy2(report, cache_dir / report.name)
        print("[PASS] Artifact:", artifact)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("[FATAL]", exc, file=sys.stderr)
        raise
