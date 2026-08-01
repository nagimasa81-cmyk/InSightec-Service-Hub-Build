from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
import time
import traceback
from contextlib import contextmanager
from importlib import metadata as importlib_metadata
from pathlib import Path

from common.build_common import (
    copy_payload,
    deploy_qt_runtime,
    detect_requirements,
    read_json,
    sha256,
    smoke_test_exe,
    verify_payload,
    write_json,
)
from builders import BUILDERS


STAGES = (
    "source_validation",
    "sonication_build",
    "sonication_smoke",
    "hub_integration",
    "hub_build",
    "hub_smoke",
)


@contextmanager
def build_stage(name: str):
    previous = os.environ.get("INSIGHTEC_BUILD_STAGE")
    os.environ["INSIGHTEC_BUILD_STAGE"] = name
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("INSIGHTEC_BUILD_STAGE", None)
        else:
            os.environ["INSIGHTEC_BUILD_STAGE"] = previous


class StageLogger:
    def __init__(self, path: Path, stage: str):
        self.path = path
        self.stage = stage
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = f"[{stamp}] [{self.stage}] {message}\n"
        with self.path.open("a", encoding="utf-8", errors="replace") as stream:
            stream.write(line)
        print(line.rstrip())


class SonicationPipeline:
    """Build Sonication independently, then integrate only a verified payload.

    The Hub builder never compiles Sonication.  This class owns source validation,
    dependency auditing, compilation, standalone smoke testing, and payload copy.
    """

    def __init__(self, hub_ctx, component_ctx, hub_root: Path):
        self.hub_ctx = hub_ctx
        self.ctx = component_ctx
        self.hub_root = hub_root
        self.diag_root = hub_ctx.workspace / "diagnostics" / "sonication"
        self.artifact_root = hub_ctx.output_root / "sonication"
        self.diag_root.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.summary = {
            "schema": "insightec.sonication.pipeline.v1",
            "included": True,
            "source_zip": component_ctx.source_zip.name,
            "source_sha256": sha256(component_ctx.source_zip),
            "stages": [],
        }
        self.payload = None
        self.exe = None

    def _log(self, filename: str, stage: str) -> StageLogger:
        return StageLogger(self.diag_root / filename, stage)

    def _record(self, stage: str, status: str, started: float, **extra):
        item = {"stage": stage, "status": status, "seconds": round(time.time() - started, 2), **extra}
        self.summary["stages"].append(item)
        write_json(self.diag_root / "pipeline_summary.json", self.summary)
        write_json(self.artifact_root / "pipeline_summary.json", self.summary)
        return item

    def _copy_diagnostics(self):
        for path in self.diag_root.glob("*"):
            if path.is_file():
                shutil.copy2(path, self.artifact_root / path.name)

    def _dependency_report(self) -> dict:
        packages = [
            "PySide6", "PySide6-Essentials", "PySide6-Addons", "pyqtgraph",
            "numpy", "opencv-python", "opencv-python-headless", "Nuitka", "PyInstaller",
        ]
        package_versions = {}
        for package in packages:
            try:
                package_versions[package] = importlib_metadata.version(package)
            except importlib_metadata.PackageNotFoundError:
                package_versions[package] = None

        modules = ["PySide6", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "pyqtgraph", "numpy", "cv2"]
        module_specs = {}
        for module in modules:
            try:
                spec = importlib.util.find_spec(module)
                module_specs[module] = str(spec.origin) if spec and spec.origin else None
            except Exception as exc:
                module_specs[module] = f"ERROR: {type(exc).__name__}: {exc}"

        specs = [str(p.relative_to(self.ctx.source_root)).replace("\\", "/") for p in self.ctx.source_root.rglob("*.spec")]
        hidden_imports = []
        for path in self.ctx.source_root.rglob("*.spec"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "hiddenimports" in text:
                hidden_imports.append(str(path.relative_to(self.ctx.source_root)).replace("\\", "/"))

        return {
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "packages": package_versions,
            "modules": module_specs,
            "requirements": [str(p.relative_to(self.ctx.source_root)).replace("\\", "/") for p in detect_requirements(self.ctx.source_root)],
            "spec_files": specs,
            "spec_files_with_hidden_imports": hidden_imports,
            "path_entries": os.environ.get("PATH", "").split(os.pathsep),
        }

    def stage1_source_validation(self):
        stage = "source_validation"
        started = time.time()
        log = self._log("stage1_source_validation.log", stage)
        try:
            with build_stage(stage):
                root = self.ctx.source_root
                log.write(f"SOURCE root: {root}")
                required_unique = {
                    "version.json": list(root.rglob("version.json")),
                    "VERSION": list(root.rglob("VERSION")),
                    "constants.py": list(root.rglob("src/common/constants.py")),
                    "insightec_build_contract.json": list(root.rglob("insightec_build_contract.json")),
                }
                for label, matches in required_unique.items():
                    if len(matches) != 1:
                        raise RuntimeError(f"Expected one {label}; found {len(matches)}")
                    log.write(f"{label}: {matches[0].relative_to(root)}")

                version = read_json(required_unique["version.json"][0])
                if not str(version.get("version", "")).strip() or not str(version.get("commit", "")).strip():
                    raise RuntimeError("version.json requires non-empty version and commit")

                build_script = root / str(self.ctx.build_config.get("build_script") or "")
                entry_point = root / str(self.ctx.build_config.get("entry_point") or self.ctx.entry_point or "")
                if not build_script.is_file():
                    raise FileNotFoundError(f"Configured build script missing: {build_script}")
                if not entry_point.is_file():
                    raise FileNotFoundError(f"Configured entry point missing: {entry_point}")
                log.write(f"Build script: {build_script.relative_to(root)}")
                log.write(f"Entry point: {entry_point.relative_to(root)}")

                manifests = list(root.rglob("manifest.json"))
                pyprojects = list(root.rglob("pyproject.toml"))
                specs = list(root.rglob("*.spec"))
                log.write(f"manifest.json count: {len(manifests)}")
                log.write(f"pyproject.toml count: {len(pyprojects)}")
                log.write(f"*.spec count: {len(specs)}")

                report = self._dependency_report()
                write_json(self.diag_root / "build_environment.json", report)
                write_json(self.diag_root / "runtime_dependencies.json", report)
                log.write("Dependency inventory written")
                self._record(stage, "pass", started, build_script=str(build_script), entry_point=str(entry_point))
        except Exception as exc:
            log.write(f"FAILED: {type(exc).__name__}: {exc}")
            (self.diag_root / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
            self._record(stage, "fail", started, error=f"{type(exc).__name__}: {exc}")
            self._copy_diagnostics()
            raise
        self._copy_diagnostics()

    def _ensure_deterministic_nuitka(self, log: StageLogger):
        """Reset the shared runner toolchain before the dedicated Sonication build.

        Hub assembly builds several modules in one Python environment. A previous
        module can install an older Nuitka release. The Sonication BAT requests
        ``nuitka`` without ``--upgrade``, so pip may keep that older release and
        produce a frozen EXE that omits PySide6.QtOpenGL. Run 47 proved that
        Nuitka 4.1.3 packages the current PySide6/pyqtgraph set correctly.
        """
        import subprocess

        required = "Nuitka==4.1.3"
        command = [
            sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check", "--upgrade",
            required, "ordered-set", "zstandard",
        ]
        log.write("Resetting Sonication compiler toolchain: " + " ".join(command))
        completed = subprocess.run(
            command, cwd=str(self.ctx.source_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        (self.diag_root / "stage2_toolchain_install.log").write_text(output, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"Failed to install deterministic Sonication toolchain: {required}")

        probe = subprocess.run(
            [sys.executable, "-c",
             "import nuitka, PySide6, PySide6.QtOpenGL, PySide6.QtOpenGLWidgets, pyqtgraph; "
             "import importlib.metadata as m; "
             "print('Nuitka=' + m.version('Nuitka')); "
             "print('PySide6=' + PySide6.__version__); "
             "print('pyqtgraph=' + pyqtgraph.__version__); "
             "print('QtOpenGL=' + PySide6.QtOpenGL.__file__); "
             "print('QtOpenGLWidgets=' + PySide6.QtOpenGLWidgets.__file__)"],
            cwd=str(self.ctx.source_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        probe_text = (probe.stdout or "") + (probe.stderr or "")
        (self.diag_root / "stage2_toolchain_probe.log").write_text(probe_text, encoding="utf-8")
        if probe.returncode != 0:
            raise RuntimeError("Sonication toolchain probe failed before compilation")
        if "Nuitka=4.1.3" not in probe_text:
            raise RuntimeError("Sonication toolchain version mismatch; expected Nuitka 4.1.3")
        log.write(probe_text.strip().replace("\n", " | "))

    def stage2_build(self):
        stage = "sonication_build"
        started = time.time()
        log = self._log("stage2_build.log", stage)
        try:
            with build_stage(stage):
                self.ctx.build_stage = stage
                self._ensure_deterministic_nuitka(log)
                self.ctx.log_path = self.diag_root / "stage2_builder_output.log"
                log.write(f"Builder: {self.ctx.builder_name}; engine: {self.ctx.engine}")
                self.payload, self.exe = BUILDERS[self.ctx.builder_name](self.ctx).build()
                log.write(f"Payload: {self.payload}")
                log.write(f"Executable: {self.exe}")
                if not self.exe.is_file():
                    raise FileNotFoundError(f"Sonication executable missing: {self.exe}")
                # Keep an immediately inspectable executable plus the complete runtime payload.
                shutil.copy2(self.exe, self.artifact_root / "sonication.exe")
                payload_artifact = self.artifact_root / "build_payload"
                copy_payload(self.payload, payload_artifact)
                self._record(stage, "pass", started, exe=str(self.exe), payload=str(self.payload), exe_size=self.exe.stat().st_size)
        except Exception as exc:
            log.write(f"FAILED: {type(exc).__name__}: {exc}")
            (self.diag_root / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
            self._record(stage, "fail", started, error=f"{type(exc).__name__}: {exc}")
            self._copy_diagnostics()
            raise
        self._copy_diagnostics()

    def stage3_smoke(self):
        stage = "sonication_smoke"
        started = time.time()
        log = self._log("stage3_smoke.log", stage)
        try:
            with build_stage(stage):
                if self.payload is None or self.exe is None:
                    raise RuntimeError("Stage2 payload is unavailable")
                qt = deploy_qt_runtime(self.payload, self.exe, self.ctx.source_root, self.diag_root / "stage3_qt_deploy.log")
                verified = verify_payload(self.payload, self.exe, self.ctx.source_root)
                smoke = smoke_test_exe(self.exe, self.diag_root / "stage3_smoke_process.log", seconds=15)
                source_startup = self.ctx.workspace / "diagnostics" / "startup_error.log"
                if source_startup.is_file():
                    shutil.copy2(source_startup, self.diag_root / "startup_error.log")
                log.write(f"Qt deployment: {qt}")
                log.write(f"Payload verification: {verified}")
                log.write(f"Smoke result: {smoke}")
                self._record(stage, "pass", started, qt=qt, payload_check=verified, smoke=smoke)
        except Exception as exc:
            log.write(f"FAILED: {type(exc).__name__}: {exc}")
            (self.diag_root / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
            startup = self.diag_root / "startup_error.log"
            if not startup.exists():
                startup.write_text(str(exc) + "\n", encoding="utf-8")
            self._record(stage, "fail", started, error=f"{type(exc).__name__}: {exc}")
            self._copy_diagnostics()
            raise
        self._copy_diagnostics()

    def stage4_integrate(self, target: Path, preserved: dict[str, bytes] | None = None):
        stage = "hub_integration"
        started = time.time()
        log = self._log("stage4_integration.log", stage)
        try:
            with build_stage(stage):
                if self.payload is None or self.exe is None:
                    raise RuntimeError("Verified Sonication payload is unavailable")
                copy_payload(self.payload, target)
                for name, data in (preserved or {}).items():
                    (target / name).write_bytes(data)
                copied_exe = target / self.exe.name
                if not copied_exe.is_file():
                    candidates = list(target.rglob(self.exe.name))
                    if not candidates:
                        raise FileNotFoundError(f"Integrated Sonication EXE missing: {self.exe.name}")
                    copied_exe = candidates[0]

                config = read_json(self.hub_root / "config.json")
                version = read_json(self.hub_root / "version.json")
                config_text = json.dumps(config, ensure_ascii=False).lower()
                version_text = json.dumps(version, ensure_ascii=False).lower()
                if "sonication" not in config_text:
                    raise RuntimeError("Hub config/registry does not expose Sonication in include mode")
                if "sonication" not in version_text:
                    raise RuntimeError("Hub version.json does not expose Sonication in include mode")
                log.write(f"Integrated payload: {target}")
                log.write(f"Integrated EXE: {copied_exe.relative_to(self.hub_root)}")
                self._record(stage, "pass", started, target=str(target), exe=str(copied_exe))
        except Exception as exc:
            log.write(f"FAILED: {type(exc).__name__}: {exc}")
            (self.diag_root / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
            self._record(stage, "fail", started, error=f"{type(exc).__name__}: {exc}")
            self._copy_diagnostics()
            raise
        self._copy_diagnostics()

    def mark_stage(self, number: int, stage: str, status: str, details: dict | None = None):
        filename = f"stage{number}_{stage}.log"
        started = time.time()
        log = self._log(filename, stage)
        log.write(status.upper())
        if details:
            log.write(json.dumps(details, ensure_ascii=False, default=str))
        self._record(stage, status, started, **(details or {}))
        self._copy_diagnostics()

    def finalize(self):
        self.summary["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(self.diag_root / "pipeline_summary.json", self.summary)
        write_json(self.artifact_root / "pipeline_summary.json", self.summary)
        self._copy_diagnostics()
