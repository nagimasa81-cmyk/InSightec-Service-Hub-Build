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
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = ROOT / "Module"
CACHE_ROOT = ROOT / ".rc9_cache"
OUTPUT_ROOT = ROOT / "artifacts"
PYTHON_VERSION = "3.14"
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
    source_zip: str


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


def metadata(root: Path) -> dict:
    path = root / "version.json"
    if not path.is_file():
        raise FileNotFoundError("version.json is required by RC9.")
    data = load_json(path)
    if not data.get("version"):
        raise ValueError("version.json: version is required.")
    return data


def actual_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def cache_key(source: Path, opts: Options) -> str:
    pieces = [sha256_file(source), sha256_file(Path(__file__)), actual_python_version(), str(opts.hub_guide), str(opts.module_guide), opts.hub_variant]
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
    options = {
        "schema": "rc9",
        "hub_variant": actual or opts.hub_variant,
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
        config["hub_variant"] = actual or opts.hub_variant
        config["settings_source"] = "build_options.json"
        write_json(config_path, config)
    os.environ.update({
        "INSIGHTEC_HUB_VARIANT": actual or opts.hub_variant,
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


def build(stage: Path, meta: dict) -> None:
    spec = choose_spec(stage, meta)
    if spec:
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", spec.name], stage)
        return
    requested_builder = str(meta.get("build_script", "")).strip()
    builder_candidates = ([stage / requested_builder] if requested_builder else []) + [stage / "Build_Hub_EXE.py", stage / "build.py"]
    builder = next((p for p in builder_candidates if p.is_file() and p.resolve() != Path(__file__).resolve()), None)
    if builder:
        run([sys.executable, builder.name], stage)
        return
    bats = [stage / n for n in ("01_BUILD_EXE_NUITKA.bat", "BUILD_EXE_NUITKA.bat", "BUILD_EXE.bat", "build.bat", "01_BUILD_EXE.bat")]
    bat = next((p for p in bats if p.is_file() and not is_rc9_wrapper_bat(p)), None)
    if bat and os.name == "nt":
        run(["cmd.exe", "/d", "/c", bat.name], stage)
        return
    entry = choose_entry(stage, meta)
    if not entry:
        raise RuntimeError("No unambiguous SPEC, builder, usable BAT, pyproject entry, or Python entry point.")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", entry.stem, str(entry.relative_to(stage))], stage)


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


def artifact_filename(module: str, variant: str, version: str, guide: bool) -> str:
    key = f"{module}:{variant}" if module == HUB_MODULE else module
    base = ARTIFACT_NAMES.get(key, re.sub(r"[^A-Za-z0-9]", "", module))
    clean = re.sub(r"(?i)^RC", "", str(version)).strip()
    return f"{base}_RC{clean}{'G' if guide else ''}.zip"


def make_zip(payload: Path, output: Path, stage: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(".zip.tmp")
    if temp.exists(): temp.unlink()
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(payload.rglob("*")):
            if path.is_file() and path.suffix.lower() != ".zip":
                archive.write(path, path.relative_to(payload))
        for name in ("version.json", "build_options.json", "hub_manifest.json", "manifest.json"):
            path = stage / name
            if path.is_file() and not (payload / name).exists():
                archive.write(path, name)
    temp.replace(output)


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


def inspect_artifact(artifact: Path, opts: Options | None = None, meta: dict | None = None) -> tuple[bool, bool, bool, bool, bool]:
    if not artifact.is_file() or artifact.stat().st_size == 0 or not zipfile.is_zipfile(artifact):
        return False, False, False, False, False
    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
        safe = all(name and not name.startswith(("/", "\\")) and ".." not in Path(name).parts for name in names)
        no_double = not any(name.lower().endswith(".zip") for name in names)
        has_exe = any(name.lower().endswith(".exe") for name in names)
        has_options = "build_options.json" in names
        manifest_name = "hub_manifest.json" if opts and opts.module_name == HUB_MODULE else "manifest.json"
        manifest_ok = False
        if opts and meta and manifest_name in names:
            try:
                manifest_ok = validate_manifest_data(json.loads(archive.read(manifest_name).decode("utf-8-sig")), opts, meta)
            except Exception:
                manifest_ok = False
    return safe, no_double, has_exe, has_options, manifest_ok

def run_triple_check(stage: Path, payload: Path, exe: Path, artifact: Path, opts: Options, meta: dict) -> dict[str, bool]:
    safe, no_double, has_exe, has_options, artifact_manifest = inspect_artifact(artifact, opts, meta)
    options = load_json(stage / "build_options.json")
    return {
        "version.json": (stage / "version.json").is_file() and bool(meta.get("version")),
        "manifest": validate_manifest(stage, opts, meta) and artifact_manifest,
        "Module": opts.module_name in find_modules(),
        "ZIP structure": safe and has_exe and has_options,
        "BAT": any(stage.rglob("*.bat")),
        "SPEC/build definition": bool(any(stage.rglob("*.spec")) or any(stage.rglob("Build_*EXE.py")) or (stage / "pyproject.toml").is_file() or choose_entry(stage, meta)),
        "Python syntax": python_syntax_check(stage) >= 1,
        "dist generated": payload.is_dir() and any(payload.iterdir()),
        "EXE generated": exe.is_file() and exe.stat().st_size > 0,
        "Artifact generated": artifact.is_file() and artifact.stat().st_size > 0,
        "No double ZIP": no_double,
        "Hub Variant": opts.module_name != HUB_MODULE or meta.get("hub_variant") == opts.hub_variant,
        "Guide settings": options.get("hub_guide_enabled") == opts.hub_guide and options.get("module_guide_enabled") == opts.module_guide and has_options,
        "Python version": actual_python_version() == PYTHON_VERSION,
    }


def write_report(path: Path, checks: dict[str, bool], key: str, source: Path, artifact: Path, opts: Options) -> None:
    write_json(path, {"schema": "rc9", "result": "PASS" if all(checks.values()) else "FAIL", "cache_key": key,
        "source_sha256": sha256_file(source), "build_py_sha256": sha256_file(Path(__file__)), "artifact": artifact.name,
        "artifact_sha256": sha256_file(artifact) if artifact.is_file() else "", "python_version": actual_python_version(),
        "hub_variant": opts.hub_variant, "hub_guide_enabled": opts.hub_guide, "module_guide_enabled": opts.module_guide, "checks": checks})


def save_cache(cache_dir: Path, artifact: Path, report: Path) -> bool:
    cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, cache_dir / artifact.name)
    shutil.copy2(report, cache_dir / report.name)
    return sha256_file(cache_dir / artifact.name) == sha256_file(artifact)


def restore_cache(cache_dir: Path, key: str, source: Path, opts: Options) -> bool:
    reports = sorted(cache_dir.glob("*.triple_check.json")) if cache_dir.is_dir() else []
    if not reports: return False
    try:
        report = load_json(reports[-1]); artifact = cache_dir / report["artifact"]
        safe, no_double, has_exe, has_options, _ = inspect_artifact(artifact)
        valid = all([report.get("result") == "PASS", report.get("cache_key") == key,
            report.get("source_sha256") == sha256_file(source), report.get("build_py_sha256") == sha256_file(Path(__file__)),
            report.get("artifact_sha256") == sha256_file(artifact), report.get("python_version") == actual_python_version(),
            report.get("hub_variant") == opts.hub_variant, report.get("hub_guide_enabled") == opts.hub_guide,
            report.get("module_guide_enabled") == opts.module_guide, safe, no_double, has_exe, has_options,
            all(report.get("checks", {}).values())])
    except Exception as exc:
        print("[WARN] Cache validation failed:", exc); return False
    if not valid: return False
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, OUTPUT_ROOT / artifact.name); shutil.copy2(reports[-1], OUTPUT_ROOT / reports[-1].name)
    print("[PASS] Cache restored:", artifact.name); return True


def prune_cache(limit: int = 20) -> None:
    if not CACHE_ROOT.is_dir(): return
    dirs = sorted((p for p in CACHE_ROOT.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for old in dirs[limit:]: shutil.rmtree(old, ignore_errors=True)


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
    if not module: raise ValueError("Module name is required when Build Target is Module.")
    if args.hub_variant not in {"card_launcher", "zip_drop"}: raise ValueError("Invalid Hub Variant.")
    if actual_python_version() != PYTHON_VERSION: raise RuntimeError(f"RC9 requires Python {PYTHON_VERSION}; active={actual_python_version()}")
    return Options(args.build_target, module, args.hub_variant, as_bool(args.hub_guide), as_bool(args.module_guide), args.source_zip)


def main() -> int:
    opts = parse_args(); modules = find_modules()
    if opts.module_name not in modules: raise ValueError(f"Unknown module: {opts.module_name}. Detected: {', '.join(modules)}")
    source = select_source(MODULE_ROOT / opts.module_name, opts.source_zip)
    key = cache_key(source, opts); cache_dir = CACHE_ROOT / key
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True); OUTPUT_ROOT.mkdir(parents=True)
    CACHE_ROOT.mkdir(exist_ok=True); prune_cache()
    print("[INFO] SOURCE:", source); print("[INFO] Cache Key:", key)
    if restore_cache(cache_dir, key, source, opts): return 0
    with tempfile.TemporaryDirectory(prefix="rc9_") as temp:
        extract = Path(temp) / "extract"; extract.mkdir(); safe_extract(source, extract)
        root = unwrap(extract); meta = metadata(root); stage = Path(temp) / "stage"; copy_source(root, stage)
        apply_options(stage, opts, meta); ensure_rc9_manifest(stage, opts, meta); install_requirements(stage); build(stage, meta)
        payload, exe = find_distribution(stage)
        guide = opts.hub_guide if opts.module_name == HUB_MODULE else opts.module_guide
        artifact = OUTPUT_ROOT / artifact_filename(opts.module_name, opts.hub_variant, str(meta["version"]), guide)
        candidate_dir = Path(temp) / "candidate"
        candidate_dir.mkdir()
        candidate = candidate_dir / artifact.name
        make_zip(payload, candidate, stage)
        checks = run_triple_check(stage, payload, exe, candidate, opts, meta)
        failed = [name for name, ok in checks.items() if not ok]
        for name, ok in checks.items(): print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if failed:
            raise RuntimeError("Triple Check failed before Artifact publication: " + ", ".join(failed))
        shutil.copy2(candidate, artifact)
        report = artifact.with_suffix(".triple_check.json")
        write_report(report, checks, key, source, artifact, opts)
        checks["Cache"] = save_cache(cache_dir, artifact, report)
        if not checks["Cache"]:
            artifact.unlink(missing_ok=True)
            report.unlink(missing_ok=True)
            raise RuntimeError("Triple Check failed: Cache")
        write_report(report, checks, key, source, artifact, opts)
        shutil.copy2(report, cache_dir / report.name)
        print("[PASS] Cache")
        print("[PASS] Artifact:", artifact)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
