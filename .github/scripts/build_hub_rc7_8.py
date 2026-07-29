from __future__ import annotations

import argparse
import ast
import fnmatch
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
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTRACT_NAME = "insightec_build_contract.json"
CONTRACT_SCHEMA = "insightec-build-contract/v1"
CONTRACT_VERSION = 9
MODULES = {
    "Hub": "InSightec_Service_hub",
    "DOanalysis": "DO_Analysis",
    "TrackerSNR": "trackerSNR",
    "LogExplorer": "Log_explorer",
    "SonicationAnalysis": "Soni",
    "FUSImageExplore": "FFT",
    "VIMeasure": "VIMeasure",
}
TOOL_ORDER = ["DOanalysis", "TrackerSNR", "LogExplorer", "SonicationAnalysis", "FUSImageExplore", "VIMeasure"]


@dataclass
class Candidate:
    module_id: str
    display_name: str
    zip_path: Path
    sha256: str
    contract: dict[str, Any]
    contract_member: str
    temporary: bool = False


class BuildFailure(RuntimeError):
    pass


def log(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88, flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reconstruct_split(base_name: str, parts: list[Path], destination: Path) -> Path:
    ordered = sorted(parts, key=lambda p: int(re.search(r"\.part(\d+)$", p.name, re.I).group(1)))
    expected = 1
    for part in ordered:
        number = int(re.search(r"\.part(\d+)$", part.name, re.I).group(1))
        if number != expected:
            raise BuildFailure(f"{base_name}: missing part{expected:03d}; found {part.name}")
        if part.stat().st_size <= 0:
            raise BuildFailure(f"{part}: empty split part")
        if part.stat().st_size >= 25 * 1024 * 1024:
            raise BuildFailure(f"{part}: split part must be below 25 MB")
        expected += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as out:
        for part in ordered:
            print(f"  append {part.name}")
            with part.open("rb") as src:
                shutil.copyfileobj(src, out, length=1024 * 1024)
    return destination


def inspect_contract(zip_path: Path, expected_module: str) -> tuple[dict[str, Any], str] | None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            bad = zf.testzip()
            if bad:
                raise BuildFailure(f"{zip_path.name}: corrupted member {bad}")
            members = [n for n in zf.namelist() if n.endswith(CONTRACT_NAME)]
            matches: list[tuple[dict[str, Any], str]] = []
            for member in members:
                try:
                    data = json.loads(zf.read(member).decode("utf-8-sig"))
                except Exception as exc:
                    raise BuildFailure(f"{zip_path.name}:{member}: invalid contract JSON: {exc}") from exc
                if data.get("module_id") == expected_module:
                    matches.append((data, member))
            if not matches:
                return None
            if len(matches) != 1:
                raise BuildFailure(f"{zip_path.name}: multiple contracts found for {expected_module}: {[m for _, m in matches]}")
            return matches[0]
    except zipfile.BadZipFile as exc:
        raise BuildFailure(f"{zip_path}: invalid ZIP: {exc}") from exc


def enumerate_candidates(workspace: Path, module_id: str, module_folder: str, temp_root: Path) -> tuple[list[Candidate], list[str]]:
    module_dir = workspace / "Module" / module_folder
    errors: list[str] = []
    if not module_dir.is_dir():
        return [], [f"Module/{module_folder}: folder is missing"]
    files = [p for p in module_dir.rglob("*") if p.is_file()]
    normal = [p for p in files if re.search(r"_SOURCE\.zip$", p.name, re.I)]
    groups: dict[str, list[Path]] = {}
    for p in files:
        m = re.match(r"^(.+\.zip)\.part(\d{3,})$", p.name, re.I)
        if m:
            groups.setdefault(m.group(1), []).append(p)

    raw: list[tuple[str, Path, bool]] = [(p.name, p, False) for p in normal]
    for base, parts in groups.items():
        try:
            rebuilt = reconstruct_split(base, parts, temp_root / module_id / base)
            raw.append((base, rebuilt, True))
        except Exception as exc:
            errors.append(str(exc))

    candidates: list[Candidate] = []
    ignored: list[str] = []
    for display, path, temporary in raw:
        try:
            found = inspect_contract(path, module_id)
            if not found:
                ignored.append(display)
                continue
            contract, member = found
            candidates.append(Candidate(module_id, display, path, sha256(path), contract, member, temporary))
        except Exception as exc:
            errors.append(str(exc))
    if ignored:
        print(f"  ignored legacy/uncontracted SOURCE for {module_id}: {', '.join(sorted(ignored))}")
    return candidates, errors


def choose_candidate(candidates: list[Candidate], module_id: str) -> Candidate:
    if not candidates:
        raise BuildFailure(f"{module_id}: no RC7 contracted SOURCE package found")
    candidates.sort(key=lambda c: (int(c.contract.get("release_sequence", -1)), c.display_name), reverse=True)
    best = candidates[0]
    same = [c for c in candidates if int(c.contract.get("release_sequence", -1)) == int(best.contract.get("release_sequence", -1))]
    hashes = {c.sha256 for c in same}
    if len(hashes) > 1:
        names = ", ".join(c.display_name for c in same)
        raise BuildFailure(f"{module_id}: ambiguous SOURCE packages share release_sequence={best.contract.get('release_sequence')}: {names}")
    return best


def extract_candidate(candidate: Candidate, root: Path) -> Path:
    target = root / candidate.module_id
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    with zipfile.ZipFile(candidate.zip_path) as zf:
        zf.extractall(target)
    member_parent = Path(candidate.contract_member).parent
    app_root = target / member_parent
    if not app_root.is_dir():
        raise BuildFailure(f"{candidate.module_id}: contract root does not exist: {app_root}")
    return app_root



QT_SYMBOL_MODULES = {
    "QTimer": "PySide6.QtCore", "QObject": "PySide6.QtCore", "Signal": "PySide6.QtCore",
    "Slot": "PySide6.QtCore", "QSize": "PySide6.QtCore", "QRect": "PySide6.QtCore",
    "QPoint": "PySide6.QtCore", "QFile": "PySide6.QtCore", "QDir": "PySide6.QtCore",
}


def imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def used_load_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}


def validate_runtime_symbols(app_root: Path, module_id: str) -> list[str]:
    errors: list[str] = []
    for py in app_root.rglob("*.py"):
        if any(part.lower() in {"tests", "test", ".venv_nuitka", "build", "dist", "docs"} for part in py.parts):
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(py))
        except SyntaxError as exc:
            errors.append(f"{module_id}: Python syntax error in {py.relative_to(app_root)}: {exc}")
            continue
        imported = imported_names(tree)
        used = used_load_names(tree)
        for symbol, origin in QT_SYMBOL_MODULES.items():
            if symbol in used and symbol not in imported and not hasattr(__builtins__, symbol):
                errors.append(f"{module_id}: {py.relative_to(app_root)} uses {symbol} but does not import it from {origin}")
    return errors


def validate_qt_nuitka_contract(candidate: Candidate, app_root: Path, build_file: Path) -> list[str]:
    errors: list[str] = []
    build = candidate.contract.get("build", {})
    required = [str(x) for x in build.get("required_nuitka_modules", [])]
    if not required or not build_file.is_file():
        return errors
    text = build_file.read_text(encoding="utf-8", errors="ignore")
    included = set(re.findall(r"--include-module=([A-Za-z0-9_.-]+)", text))
    for module in required:
        if module not in included:
            errors.append(f"{candidate.module_id}: required Nuitka module is not included: {module}")
    return errors

def validate_contract(candidate: Candidate, app_root: Path) -> list[str]:
    c = candidate.contract
    errors: list[str] = []
    def need(condition: bool, message: str) -> None:
        if not condition:
            errors.append(f"{candidate.module_id}: {message}")
    need(c.get("contract_schema") == CONTRACT_SCHEMA, "contract_schema mismatch")
    need(int(c.get("contract_version", -1)) >= CONTRACT_VERSION, "contract_version is below 7")
    need(c.get("module_folder") == MODULES[candidate.module_id], f"module_folder must be {MODULES[candidate.module_id]}")
    need(int(c.get("release_sequence", -1)) >= 0, "release_sequence is missing")
    release = c.get("release_mode", {})
    need(release.get("environment_variable") == "INSIGHTEC_RELEASE_MODE", "release-mode variable mismatch")
    need(str(release.get("value")) == "1", "release-mode value must be 1")
    need(release.get("guide_tour_enabled") is False, "guide/tour must be disabled in release")
    marker = app_root / str(c.get("root_marker", ""))
    need(marker.is_file(), f"root marker missing: {marker.name}")
    build = c.get("build", {})
    build_file = app_root / str(build.get("file", ""))
    need(build.get("mode") == "bat", "only BAT build mode is accepted for RC7")
    need(build_file.is_file(), f"selected build BAT missing: {build_file}")
    need(bool(build.get("expected_exe_patterns")), "expected_exe_patterns is empty")
    if build_file.is_file():
        text = build_file.read_text(encoding="utf-8", errors="ignore").lower()
        for token in build.get("forbidden_tokens", []):
            if str(token).lower() in text:
                errors.append(f"{candidate.module_id}: forbidden token in selected BAT: {token}")
    # RC7.7: statically validate Nuitka include-package names before dependencies/build.
    if build_file.is_file():
        bat_text = build_file.read_text(encoding="utf-8", errors="ignore")
        include_pkgs = re.findall(r"--include-package=([A-Za-z0-9_.-]+)", bat_text)
        forbidden = {str(x).lower() for x in build.get("forbidden_nuitka_packages", [])}
        # Known distribution-name/import-name mismatches that Nuitka cannot include as packages.
        globally_invalid = {
            "pylibjpeg_libjpeg", "pylibjpeg_openjpeg",
            "pylibjpeg.libjpeg", "pylibjpeg.openjpeg",
        }
        forbidden |= globally_invalid
        for package_name in include_pkgs:
            if package_name.lower() in forbidden:
                errors.append(f"{candidate.module_id}: invalid/non-importable Nuitka package requested: {package_name}")
        if candidate.module_id == "FUSImageExplore":
            required_decoder_imports = {"pylibjpeg", "libjpeg", "openjpeg"}
            missing_decoder_imports = sorted(required_decoder_imports - {x.lower() for x in include_pkgs})
            if missing_decoder_imports:
                errors.append(f"{candidate.module_id}: decoder packages missing from Nuitka include list: {', '.join(missing_decoder_imports)}")
            expected_probe = "import pydicom, pylibjpeg, libjpeg, openjpeg"
            if expected_probe not in bat_text.lower():
                errors.append(f"{candidate.module_id}: selected BAT lacks decoder import probe: {expected_probe}")
        probes = [str(x) for x in build.get("python_import_probe", [])]
        if probes:
            # Support both simple imports and explicit from-import probes.
            for probe in probes:
                token = probe.split(".")[-1] if probe.startswith("PySide6.") else probe
                if token.lower() not in bat_text.lower():
                    errors.append(f"{candidate.module_id}: selected BAT lacks import probe marker: {probe}")
        errors.extend(validate_qt_nuitka_contract(candidate, app_root, build_file))

    errors.extend(validate_runtime_symbols(app_root, candidate.module_id))

    if candidate.module_id == "Hub":
        need(c.get("external_tool_assembly") is True, "external_tool_assembly contract must be true")
        need(not (app_root / "integrated_sources").exists(), "integrated_sources must not be bundled in RC7 Hub SOURCE")
        bundled_exes = list((app_root / "tools").rglob("*.exe")) if (app_root / "tools").exists() else []
        need(not bundled_exes, "prebuilt tool EXEs must not be bundled in Hub SOURCE")
        builder = app_root / "Build_Hub_EXE.py"
        need(builder.is_file(), "Build_Hub_EXE.py is missing")
        if builder.is_file():
            need("INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY" in builder.read_text(encoding="utf-8", errors="ignore"),
                 "Build_Hub_EXE.py lacks external assembly support")
    return errors



def run_declared_source_validator(candidate: Candidate, app_root: Path) -> list[str]:
    """Run the package validator during global preflight, before any build starts."""
    errors: list[str] = []
    validator_name = str(candidate.contract.get("source_validator") or "")
    if not validator_name:
        fallback = app_root / "validate_source.py"
        if fallback.is_file():
            validator_name = "validate_source.py"
    if not validator_name:
        return errors
    validator = app_root / validator_name
    if not validator.is_file():
        return [f"{candidate.module_id}: declared source validator missing: {validator_name}"]
    env = os.environ.copy()
    env["INSIGHTEC_RELEASE_MODE"] = "1"
    env["INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, str(validator)],
            cwd=app_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except Exception as exc:
        return [f"{candidate.module_id}: source validator could not run: {exc}"]
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        tail = "\n".join(output.splitlines()[-30:])
        errors.append(
            f"{candidate.module_id}: source validator failed before compilation "
            f"(exit={result.returncode}, file={validator_name}):\n{tail}"
        )
    else:
        print(f"  [PASS] source validator: {validator_name}")
    return errors


def validate_declared_runtime_directories(candidate: Candidate, app_root: Path) -> list[str]:
    errors: list[str] = []
    declared = candidate.contract.get("required_runtime_directories", [])
    for name in declared:
        path = app_root / str(name)
        if not path.is_dir():
            errors.append(f"{candidate.module_id}: required runtime directory missing: {name}/")
        elif not any(path.iterdir()):
            errors.append(f"{candidate.module_id}: required runtime directory is empty and may be lost in ZIP: {name}/")
    return errors

def compile_python(app_root: Path, module_id: str) -> list[str]:
    errors: list[str] = []
    for p in app_root.rglob("*.py"):
        rel = p.relative_to(app_root).as_posix().lower()
        if any(part in rel for part in ("/tests/", "/test/", "/examples/", "/backup/", "/old/")) or p.name.startswith("test_"):
            continue
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as exc:
            errors.append(f"{module_id}: Python syntax failure in {p.relative_to(app_root)}: {exc}")
    return errors



def safe_zip_members(zip_path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            pp = Path(name)
            if pp.is_absolute() or ".." in pp.parts:
                errors.append(f"unsafe ZIP member: {name}")
            if info.file_size > 2 * 1024 * 1024 * 1024:
                errors.append(f"unreasonably large ZIP member: {name}")
    return errors


def bat_call_graph(app_root: Path, selected: Path) -> tuple[list[Path], list[str]]:
    seen: set[Path] = set()
    chain: list[Path] = []
    errors: list[str] = []
    def walk(path: Path) -> None:
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        if not path.is_file():
            # Activation scripts and generated venv files legitimately do not exist before build.
            if any(part.lower().startswith('.venv') for part in path.parts):
                return
            errors.append(f"called BAT is missing: {path}")
            return
        chain.append(path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        variables: dict[str, str] = {}
        for raw in text.splitlines():
            mset = re.match(r'(?i)^\s*set\s+"?([^=\"]+)=([^\"]*)"?\s*$', raw)
            if mset:
                variables[mset.group(1).strip().upper()] = mset.group(2).strip()
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.lower().startswith("rem ") or line.startswith("::"):
                continue
            m = re.match(r'(?i)^call\s+(?:"([^"]+\.bat)"|([^\s]+\.bat))', line)
            if not m:
                continue
            ref = (m.group(1) or m.group(2)).replace("%~dp0", str(path.parent) + os.sep)
            for key, value in variables.items():
                ref = re.sub(rf'%{re.escape(key)}%', value, ref, flags=re.I)
            ref = os.path.expandvars(ref)
            called = Path(ref)
            if not called.is_absolute():
                called = path.parent / called
            walk(called)
    walk(selected)
    return chain, errors


def expanded_build_text(app_root: Path, chain: list[Path]) -> str:
    chunks: list[str] = []
    for p in chain:
        text = p.read_text(encoding="utf-8", errors="ignore")
        variables: dict[str, str] = {}
        for raw in text.splitlines():
            m = re.match(r'(?i)^\s*set\s+"?([^=\"]+)=([^\"]*)"?\s*$', raw)
            if m:
                variables[m.group(1).strip().upper()] = m.group(2).strip()
        expanded = text
        for key, value in variables.items():
            expanded = re.sub(rf'%{re.escape(key)}%', value, expanded, flags=re.I)
        chunks.append(expanded)
        # Include directly invoked Python build scripts in the static contract check.
        for m in re.finditer(r'(?im)(?:python|%python_exe%|%pyexe%)\s+"?([^"\r\n ]+\.py)"?', expanded):
            q = app_root / m.group(1)
            if q.is_file():
                chunks.append(q.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)

def strong_module_checks(candidate: Candidate, app_root: Path) -> list[str]:
    c = candidate.contract
    module_id = candidate.module_id
    errors: list[str] = []
    errors.extend(f"{module_id}: {e}" for e in safe_zip_members(candidate.zip_path))
    build = c.get("build", {})
    selected = app_root / str(build.get("file", ""))
    chain, chain_errors = bat_call_graph(app_root, selected)
    errors.extend(f"{module_id}: {e}" for e in chain_errors)
    all_text = expanded_build_text(app_root, chain)
    for p in chain:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for n, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            low = line.lower()
            if low == "pause" or (low.endswith(" pause") and "if not defined ci" not in low):
                errors.append(f"{module_id}: CI-blocking pause in {p.relative_to(app_root)}:{n}")
            if re.search(r'(?i)(?:^|[ &])(?:python|py|%[^%]+%)?\s*(?:-m\s+)?(?:pytest|unittest)(?:\s|$)|(?:^|[ &])(?:python|py|%[^%]+%)?\s+tests[\\/]', line) and not low.startswith(("rem ", "::")):
                errors.append(f"{module_id}: test execution/reference in selected BAT chain {p.relative_to(app_root)}:{n}: {line}")
    if not chain:
        errors.append(f"{module_id}: selected BAT chain is empty")
    patterns = build.get("expected_exe_patterns", [])
    exact = [x for x in patterns if not any(ch in x for ch in "*?[")]
    if module_id != "Hub":
        if exact and not any(x.lower() in all_text.lower() for x in exact):
            errors.append(f"{module_id}: expected EXE name is not declared by selected BAT chain: {exact}")
        out_dirs = [str(x).lower() for x in build.get("output_directories", [])]
        if out_dirs and not any(re.search(rf'(?i)(^|[\\/\"= ]){re.escape(d)}([\\/\" ]|$)', all_text) for d in out_dirs):
            errors.append(f"{module_id}: selected BAT chain does not reference any contracted output directory: {out_dirs}")
    # Ensure the build package contains no precompiled EXE/PYD artifacts.
    prebuilt = [p for p in app_root.rglob("*") if p.is_file() and p.suffix.lower() in {".exe", ".pyd"}]
    if prebuilt:
        errors.append(f"{module_id}: source package contains prebuilt binary artifacts: {[str(p.relative_to(app_root)) for p in prebuilt[:10]]}")
    # Runtime handoff is mandatory for every analysis tool.
    if module_id != "Hub":
        py_text = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in app_root.rglob("*.py")
            if not p.name.startswith("test_") and "tests" not in {x.lower() for x in p.parts}
        )
        if "--handoff" not in py_text:
            errors.append(f"{module_id}: --handoff receiver is not implemented in runtime Python source")
        if "INSIGHTEC_HANDOFF" not in py_text:
            errors.append(f"{module_id}: INSIGHTEC_HANDOFF receiver is not implemented in runtime Python source")
        handoff_contract = c.get("handoff", {})
        if handoff_contract.get("schema") != "insightec.auto-analysis.handoff.v1":
            errors.append(f"{module_id}: build contract lacks handoff schema v1")
        if not handoff_contract.get("native_receiver"):
            errors.append(f"{module_id}: build contract does not declare a native handoff receiver")
        helper = app_root / "insightec_handoff.py"
        if not helper.is_file():
            errors.append(f"{module_id}: shared native handoff helper is missing")
        else:
            try:
                probe_dir = app_root / ".rc72_handoff_probe"
                probe_dir.mkdir(exist_ok=True)
                sample = probe_dir / "sample.log"
                sample.write_text("sample", encoding="utf-8")
                handoff_json = probe_dir / "handoff.json"
                handoff_json.write_text(json.dumps({
                    "schema": "insightec.auto-analysis.handoff.v1",
                    "tool_id": module_id,
                    "matched_files": [str(sample)],
                    "workspace_path": str(probe_dir),
                    "auto_load": True,
                    "auto_analyze": True,
                }), encoding="utf-8")
                code = (
                    "import json,sys; from insightec_handoff import load_handoff; "
                    "h=load_handoff(); assert h and h.schema=='insightec.auto-analysis.handoff.v1'; "
                    "assert len(h.input_paths())==1 and h.input_paths()[0].name=='sample.log'; "
                    "assert '--handoff' not in sys.argv; print('HANDOFF_PROBE_OK')"
                )
                env = dict(os.environ); env["PYTHONPATH"] = str(app_root)
                result = subprocess.run([sys.executable, "-c", code, "--handoff", str(handoff_json)], cwd=app_root, env=env, capture_output=True, text=True, timeout=20)
                if result.returncode != 0 or "HANDOFF_PROBE_OK" not in result.stdout:
                    errors.append(f"{module_id}: native handoff parser probe failed: {result.stdout} {result.stderr}")
                shutil.rmtree(probe_dir, ignore_errors=True)
            except Exception as exc:
                errors.append(f"{module_id}: native handoff parser probe raised: {exc}")
        receiver_markers = {
            "DOanalysis": ("do_analysis", "import_paths"),
            "TrackerSNR": ("tracker_snr", "load_inputs"),
            "LogExplorer": ("log_explorer", "viewer_selected_files"),
            "SonicationAnalysis": ("sonication_analysis", "window.load"),
            "FUSImageExplore": ("fus_image_explore", "import_paths"),
            "VIMeasure": ("vimeasure", "load_index"),
        }
        for marker in receiver_markers.get(module_id, ()):
            if marker not in py_text:
                errors.append(f"{module_id}: native handoff integration marker missing: {marker}")
    return errors


def validate_hub_tool_contracts(hub_root: Path, selected: dict[str, Candidate]) -> list[str]:
    errors: list[str] = []
    mapping = {
        "DOanalysis": "DOanalysis", "TrackerSNR": "TrackerSNR", "LogExplorer": "LogExplorer",
        "SonicationAnalysis": "SonicationAnalysis", "FUSImageExplore": "FUSImageExplore", "VIMeasure": "VIMeasure",
    }
    for mid, folder in mapping.items():
        manifest_path = hub_root / "tools" / folder / "manifest.json"
        if not manifest_path.is_file():
            errors.append(f"Hub: tool manifest missing for {mid}: {manifest_path}")
            continue
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            errors.append(f"Hub: invalid tool manifest for {mid}: {exc}")
            continue
        if m.get("handoff_schema") != "insightec.auto-analysis.handoff.v1":
            errors.append(f"Hub: {mid} manifest lacks required handoff_schema")
        handoff_meta = m.get("handoff", {})
        if handoff_meta.get("schema") != "insightec.auto-analysis.handoff.v1":
            errors.append(f"Hub: {mid} manifest handoff object is incomplete")
        if "--handoff" not in str(handoff_meta.get("argv", "")):
            errors.append(f"Hub: {mid} manifest lacks argv handoff contract")
        contract_patterns = selected[mid].contract.get("build", {}).get("expected_exe_patterns", [])
        candidates = [m.get("exe", "")] + list(m.get("executable_candidates", []))
        compatible = any(fnmatch.fnmatch(c.lower(), p.lower()) for c in candidates for p in contract_patterns if c)
        if not compatible:
            errors.append(f"Hub: {mid} manifest EXE candidates do not match contract patterns {contract_patterns}")
    hub_code = (hub_root / "InSightecServiceHub.py").read_text(encoding="utf-8", errors="ignore")
    for marker in ("--handoff", "INSIGHTEC_HANDOFF", "Auto Dataset", "workspace"):
        if marker.lower() not in hub_code.lower():
            errors.append(f"Hub: runtime integration marker missing: {marker}")
    return errors


def install_requirements(app_root: Path) -> None:
    for name in ("requirements-build.txt", "requirements.txt"):
        req = app_root / name
        if req.is_file():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], cwd=app_root, check=True)


def run_cmd_batch(batch_file: Path, *, cwd: Path, env: dict[str, str], label: str) -> int:
    """Run a BAT through cmd.exe with deterministic Windows quoting."""
    batch_file = batch_file.resolve()
    if not batch_file.is_file():
        raise BuildFailure(f"{label}: BAT does not exist: {batch_file}")
    command = ["cmd.exe", "/d", "/c", "call", str(batch_file)]
    print(f"[{label}] command: cmd.exe /d /c call <selected-bat>")
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return int(completed.returncode)


def verify_windows_batch_invocation(temp_root: Path) -> None:
    """Exercise the exact invocation with a BAT stored in a path containing spaces."""
    if os.name != "nt":
        return
    probe_dir = temp_root / "RC7.7 command probe with spaces"
    shutil.rmtree(probe_dir, ignore_errors=True)
    probe_dir.mkdir(parents=True)
    marker = probe_dir / "probe.ok"
    bat = probe_dir / "01 PROBE BUILD.bat"
    bat.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        f'>"{marker}" echo RC7_6_CMD_OK\r\n'
        "exit /b 0\r\n",
        encoding="ascii",
    )
    code = run_cmd_batch(bat, cwd=probe_dir, env=os.environ.copy(), label="CMD-PROBE")
    if code != 0 or not marker.is_file() or marker.read_text(encoding="ascii").strip() != "RC7_6_CMD_OK":
        raise BuildFailure(f"Windows BAT invocation self-test failed: exit={code}, marker={marker.exists()}")
    print("[PASS] Windows BAT invocation self-test (path with spaces).")


def run_build(app_root: Path, contract: dict[str, Any], module_id: str) -> None:
    app_root = app_root.resolve()
    build_file = (app_root / contract["build"]["file"]).resolve()
    for d in contract["build"].get("output_directories", ["dist", "output", "release"]):
        path = (app_root / d).resolve()
        try:
            build_file.relative_to(path)
            preserve = True
        except ValueError:
            preserve = False
        if path.exists() and not preserve:
            shutil.rmtree(path, ignore_errors=True)
    print(f"[{module_id}] selected SOURCE: {contract.get('source_version')} sequence={contract.get('release_sequence')}")
    print(f"[{module_id}] selected BAT: {build_file.relative_to(app_root)}")
    env = os.environ.copy()
    env["INSIGHTEC_RELEASE_MODE"] = "1"
    env["INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY"] = "1"
    return_code = run_cmd_batch(build_file, cwd=app_root, env=env, label=module_id)
    if return_code:
        raise BuildFailure(f"{module_id}: build BAT failed with exit code {return_code}")


def find_package(app_root: Path, contract: dict[str, Any], module_id: str) -> tuple[Path, Path]:
    roots = [app_root / d for d in contract["build"].get("output_directories", ["dist", "output", "release"]) if (app_root / d).is_dir()]
    if not roots:
        raise BuildFailure(f"{module_id}: no output directory created")
    exes = [p for root in roots for p in root.rglob("*.exe") if not re.search(r"debug|console|uninstall|updater|crash", p.name, re.I)]
    patterns = contract["build"].get("expected_exe_patterns", [])
    for pattern in patterns:
        matches = [p for p in exes if fnmatch.fnmatch(p.name.lower(), pattern.lower())]
        if matches:
            chosen = max(matches, key=lambda p: p.stat().st_size)
            return chosen, chosen.parent
    raise BuildFailure(f"{module_id}: expected EXE not found. Patterns={patterns}; produced={[p.name for p in exes]}")



def _collect_smoke_logs(exe: Path, stdout_text: str = "", stderr_text: str = "") -> list[str]:
    logs: list[str] = []
    if stdout_text.strip():
        logs.append("stdout:\n" + stdout_text[-6000:])
    if stderr_text.strip():
        logs.append("stderr:\n" + stderr_text[-6000:])
    names = (
        "startup_error.log",
        "VIMeasureAnalyzer_error.log",
        "MR_Image_Explorer_error.log",
        "error.log",
        "crash.log",
    )
    for name in names:
        f = exe.parent / name
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="ignore")[-6000:]
            if text.strip():
                logs.append(f"{name}:\n{text}")
    return logs


def _smoke_has_fatal_error(logs: list[str]) -> bool:
    text = "\n".join(logs).lower()
    fatal_patterns = (
        "modulenotfounderror",
        "importerror",
        "nameerror",
        "traceback (most recent call last)",
        "failed to execute script",
        "could not load the qt platform plugin",
        "qt.qpa.plugin: could not",
        "dll load failed",
        "entry point not found",
        "startup failed",
        "unhandled exception",
    )
    return any(pattern in text for pattern in fatal_patterns)


def smoke_test_executable(exe: Path, contract: dict[str, Any], module_id: str) -> None:
    """Launch a GUI executable and verify that it starts without crashing.

    GUI applications are expected to keep running. A process that remains alive for
    ``survival_seconds`` is treated as a successful startup and is then terminated by
    the workflow. An early clean exit (code 0) is also accepted for applications that
    implement a dedicated smoke-test auto-close mode.
    """
    smoke = contract.get("build", {}).get("smoke_test")
    if not smoke:
        return
    if os.name != "nt":
        print(f"[{module_id}] smoke test skipped outside Windows")
        return

    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in smoke.get("environment", {}).items()})
    survival_seconds = float(smoke.get("survival_seconds", smoke.get("startup_seconds", 5)))
    survival_seconds = max(2.0, min(survival_seconds, 30.0))
    shutdown_timeout = int(smoke.get("shutdown_timeout_seconds", 5))
    print(
        f"[{module_id}] GUI startup smoke test: {exe.name}; "
        f"required survival={survival_seconds:.1f}s"
    )

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [str(exe)],
        cwd=exe.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        creationflags=creationflags,
    )

    deadline = time.monotonic() + survival_seconds
    early_code: int | None = None
    while time.monotonic() < deadline:
        early_code = proc.poll()
        if early_code is not None:
            break
        time.sleep(0.25)

    if early_code is not None:
        stdout_text, stderr_text = proc.communicate(timeout=2)
        logs = _collect_smoke_logs(exe, stdout_text, stderr_text)
        if early_code != 0 or _smoke_has_fatal_error(logs):
            detail = "\n".join(logs)
            raise BuildFailure(
                f"{module_id}: executable exited during startup with code {early_code}.\n{detail}"
            )
        print(f"[PASS] {module_id} smoke test: clean early exit (code 0)")
        return

    # Still alive after the observation period: this is the expected behavior for GUI apps.
    logs_before_stop = _collect_smoke_logs(exe)
    if _smoke_has_fatal_error(logs_before_stop):
        proc.terminate()
        try:
            proc.wait(timeout=shutdown_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise BuildFailure(
            f"{module_id}: fatal startup marker detected while process was alive.\n"
            + "\n".join(logs_before_stop)
        )

    proc.terminate()
    try:
        stdout_text, stderr_text = proc.communicate(timeout=shutdown_timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_text, stderr_text = proc.communicate(timeout=3)

    logs = _collect_smoke_logs(exe, stdout_text, stderr_text)
    if _smoke_has_fatal_error(logs):
        raise BuildFailure(
            f"{module_id}: fatal startup marker detected after smoke-test shutdown.\n"
            + "\n".join(logs)
        )
    print(
        f"[PASS] {module_id} GUI startup smoke test: "
        f"process survived {survival_seconds:.1f}s and was stopped by the workflow"
    )

def copy_package(package_dir: Path, exe: Path, destination: Path) -> Path:
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(package_dir, destination)
    copied = destination / exe.name
    if not copied.is_file():
        raise BuildFailure(f"Copied executable missing: {copied}")
    return copied


def write_output(name: str, value: str) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")



def validate_script_runtime_imports() -> list[str]:
    """Validate that standard-library names used by this build script are imported."""
    source_path = Path(__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
            imported.update(alias.asname or alias.name for alias in node.names)

    required = {
        "time": "time",
        "subprocess": "subprocess",
        "tempfile": "tempfile",
        "shutil": "shutil",
        "json": "json",
        "os": "os",
        "re": "re",
        "zipfile": "zipfile",
        "hashlib": "hashlib",
        "argparse": "argparse",
    }
    text = source_path.read_text(encoding="utf-8")
    errors: list[str] = []
    for symbol, module in required.items():
        if re.search(rf"\b{re.escape(symbol)}\.", text) and module not in imported:
            errors.append(f"Build script uses {symbol}. but does not import {module}")
    return errors


def run_self_test() -> None:
    """Exercise helper code before any module build starts."""
    errors = validate_script_runtime_imports()
    if errors:
        raise BuildFailure("Build-script import self-check failed:\n" + "\n".join(errors))

    start = time.monotonic()
    time.sleep(0.05)
    elapsed = time.monotonic() - start
    if elapsed < 0.04:
        raise BuildFailure(f"time.monotonic/time.sleep self-test failed: elapsed={elapsed}")

    probe = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(0.4)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 2.0
    while probe.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if probe.poll() is None:
        probe.kill()
        probe.communicate(timeout=2)
        raise BuildFailure("Subprocess timing self-test timed out")
    stdout_text, stderr_text = probe.communicate(timeout=2)
    if probe.returncode != 0:
        raise BuildFailure(
            f"Subprocess timing self-test failed with {probe.returncode}: {stdout_text} {stderr_text}"
        )
    print("[PASS] RC7.8 build-script imports and timing helpers self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=os.getenv("GITHUB_WORKSPACE", "."))
    parser.add_argument("--module-name", default="InSightec_Service_hub")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        return 0
    workspace = Path(args.workspace).resolve()
    temp_root = Path(os.getenv("RUNNER_TEMP", tempfile.gettempdir())) / "insightec_rc7"
    shutil.rmtree(temp_root, ignore_errors=True)
    (temp_root / "rebuilt").mkdir(parents=True)
    (temp_root / "extract").mkdir(parents=True)

    log("RC7.8 DETERMINISTIC GLOBAL PREFLIGHT — resolve every Module before compiling anything")
    selected: dict[str, Candidate] = {}
    app_roots: dict[str, Path] = {}
    all_errors: list[str] = []
    report: dict[str, Any] = {"schema": "rc7.8-preflight-report/v1", "modules": {}, "errors": []}

    for module_id, folder in MODULES.items():
        print(f"\n[{module_id}] Module/{folder}")
        candidates, errors = enumerate_candidates(workspace, module_id, folder, temp_root / "rebuilt")
        all_errors.extend(errors)
        try:
            chosen = choose_candidate(candidates, module_id)
            selected[module_id] = chosen
            root = extract_candidate(chosen, temp_root / "extract")
            app_roots[module_id] = root
            validation = (validate_contract(chosen, root) + validate_declared_runtime_directories(chosen, root) + compile_python(root, module_id) + strong_module_checks(chosen, root) + run_declared_source_validator(chosen, root))
            all_errors.extend(validation)
            report["modules"][module_id] = {
                "module_folder": folder,
                "source": chosen.display_name,
                "sha256": chosen.sha256,
                "release_sequence": chosen.contract.get("release_sequence"),
                "source_version": chosen.contract.get("source_version"),
                "contract_member": chosen.contract_member,
                "preflight": "PASS" if not validation else "FAIL",
                "errors": validation,
            }
            print(f"  selected: {chosen.display_name}")
            print(f"  version : {chosen.contract.get('source_version')}")
            print(f"  sequence: {chosen.contract.get('release_sequence')}")
            print(f"  sha256  : {chosen.sha256}")
        except Exception as exc:
            all_errors.append(str(exc))
            report["modules"][module_id] = {"module_folder": folder, "preflight": "FAIL", "errors": [str(exc)]}

    if "Hub" in app_roots and all(mid in selected for mid in TOOL_ORDER):
        cross_errors = validate_hub_tool_contracts(app_roots["Hub"], selected)
        all_errors.extend(cross_errors)
        report["cross_module_errors"] = cross_errors

    report["errors"] = all_errors
    report["all_pass"] = not all_errors
    report_path = workspace / "RC7_8_PREFLIGHT_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nPreflight report: {report_path}")
    if all_errors:
        print("\nRC7 PREFLIGHT FOUND ALL BLOCKING ISSUES:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i:02d}. {error}")
        raise BuildFailure(f"RC7.8 deterministic build preflight failed with {len(all_errors)} issue(s). No compilation was started.")
    print("\n[PASS] All seven Module packages passed the RC7.8 deterministic build global preflight.")
    verify_windows_batch_invocation(temp_root)
    if args.preflight_only:
        return 0

    os.environ["INSIGHTEC_RELEASE_MODE"] = "1"
    os.environ["INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY"] = "1"

    # Build Hub first, then each externally sourced tool.
    log("BUILD HUB SHELL")
    hub_root = app_roots["Hub"]
    install_requirements(hub_root)
    run_build(hub_root, selected["Hub"].contract, "Hub")
    hub_exe, hub_package = find_package(hub_root, selected["Hub"].contract, "Hub")
    final_dir = hub_package
    startup_exe = hub_exe
    tools_root = final_dir / "tools"
    tools_root.mkdir(parents=True, exist_ok=True)

    status = []
    for module_id in TOOL_ORDER:
        log(f"BUILD EXTERNAL MODULE: {module_id}")
        root = app_roots[module_id]
        install_requirements(root)
        run_build(root, selected[module_id].contract, module_id)
        exe, package = find_package(root, selected[module_id].contract, module_id)
        smoke_test_executable(exe, selected[module_id].contract, module_id)
        copied = copy_package(package, exe, tools_root / module_id)
        status.append({
            "tool_id": module_id,
            "source": selected[module_id].display_name,
            "source_version": selected[module_id].contract.get("source_version"),
            "release_sequence": selected[module_id].contract.get("release_sequence"),
            "source_sha256": selected[module_id].sha256,
            "executable": copied.relative_to(final_dir).as_posix(),
            "ready": True,
        })

    status_file = final_dir / "tool_build_status.json"
    status_file.write_text(json.dumps({
        "schema": "insightec-tool-build-status/v1",
        "source": "repository_modules_rc7_7",
        "all_ready": len(status) == 6 and all(x["ready"] for x in status),
        "tools": status,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    launcher = final_dir / "RUN_APPLICATION.bat"
    relative_exe = startup_exe.relative_to(final_dir)
    launcher.write_text(f'@echo off\r\ncd /d %~dp0\r\nstart "" "{relative_exe}"\r\n', encoding="ascii")

    # Post-build contract validation.
    post_errors = []
    if not startup_exe.is_file():
        post_errors.append(f"Hub startup EXE missing: {startup_exe}")
    for item in status:
        p = final_dir / item["executable"]
        if not p.is_file():
            post_errors.append(f"Tool EXE missing after assembly: {p}")
    if not status_file.is_file() or not launcher.is_file():
        post_errors.append("Status or launcher file is missing")
    if post_errors:
        raise BuildFailure("Post-build validation failed:\n" + "\n".join(post_errors))

    print(f"FINAL DIRECTORY: {final_dir}")
    print(f"STARTUP EXE   : {startup_exe}")
    write_output("package_dir", str(final_dir))
    write_output("startup_exe", str(startup_exe))
    write_output("preflight_report", str(report_path))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildFailure as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
