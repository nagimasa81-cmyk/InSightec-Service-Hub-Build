from __future__ import annotations
import os, sys, time
from pathlib import Path
from common.build_common import detect_requirements, locate_payload, run

class BaseBuilder:
    name="base"
    def __init__(self, ctx): self.ctx=ctx

    def _fixed_file(self, configured: str, label: str) -> Path:
        if not configured:
            raise FileNotFoundError(f"Fixed {label} is not configured")
        root=self.ctx.source_root
        path=(root/configured).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            raise RuntimeError(f"Fixed {label} escapes SOURCE root: {configured}")
        if not path.is_file():
            raise FileNotFoundError(f"Fixed {label} not found: {path}")
        return path


    def _ensure_optional_qt_dependencies(self, root: Path, log: Path) -> None:
        """Force-install and verify the Qt modules required by pyqtgraph.

        A previous conditional repair could pass in one interpreter state while the
        subsequent Hub build used an Essentials-only PySide6 installation.  The Hub
        contract now requires a matching PySide6-Addons wheel whenever pyqtgraph is
        present, and records the exact package locations before compilation.
        """
        source_text = ""
        for py in root.rglob("*.py"):
            if any(part in {".venv", "venv", "site-packages", "build", "dist", "__pycache__"} for part in py.parts):
                continue
            try:
                source_text += py.read_text(encoding="utf-8", errors="ignore")[:250000]
            except Exception:
                continue
        if not any(token in source_text for token in ("pyqtgraph", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets")):
            return

        import subprocess
        version_probe = subprocess.run(
            [sys.executable, "-c", "import PySide6; print(PySide6.__version__)"],
            cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        if version_probe.returncode != 0:
            raise RuntimeError("QtOpenGL is required, but PySide6 is unavailable after requirements installation")
        version = version_probe.stdout.strip().splitlines()[-1].strip()
        package = f"PySide6-Addons=={version}"
        print(f"[REQUIRED] Installing exact Qt Addons package: {package}")
        run([
            sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
            "--upgrade", "--no-deps", package,
        ], root, log)
        run([
            sys.executable, "-c",
            "import importlib.metadata as m, PySide6, PySide6.QtOpenGL, PySide6.QtOpenGLWidgets; "
            "print('PySide6=' + PySide6.__version__); "
            "print('PySide6-Essentials=' + m.version('PySide6-Essentials')); "
            "print('PySide6-Addons=' + m.version('PySide6-Addons')); "
            "print('QtOpenGL=' + PySide6.QtOpenGL.__file__); "
            "print('QtOpenGLWidgets=' + PySide6.QtOpenGLWidgets.__file__)",
        ], root, log)

    def build(self)->tuple[Path,Path]:
        c=self.ctx; root=c.source_root; log=c.log_path; started=time.time()
        for req in detect_requirements(root):
            run([sys.executable,"-m","pip","install","-r",str(req)],req.parent,log)
        self._ensure_optional_qt_dependencies(root, log)

        cfg=c.build_config
        script=str(cfg.get("build_script") or c.version.get("build_script") or c.module_config.get("build_script") or "")
        strict=bool(cfg.get("strict_contract"))
        if strict:
            p=self._fixed_file(script,"build script")
            ep=self._fixed_file(str(cfg.get("entry_point") or c.entry_point),"entry point")
            print(f"[FIXED CONTRACT] {cfg.get('build_contract_path','')}")
            print(f"[FIXED ENTRY] {ep.relative_to(root)}")
            print(f"[FIXED BUILD SCRIPT] {p.relative_to(root)}")
            cmd=["cmd","/c",str(p)] if p.suffix.lower() in {".bat",".cmd"} else [sys.executable,str(p)]
            run(cmd,p.parent,log,env=self.build_env())
            return locate_payload(root,cfg.get("expected_exe_patterns",[]),cfg.get("output_directories",[]),started)

        # Registry-only legacy modules are still fixed: no name search and no fallback.
        p=self._fixed_file(script,"registry build script")
        ep=self._fixed_file(str(c.entry_point),"registry entry point")
        print(f"[FIXED REGISTRY ENTRY] {ep.relative_to(root)}")
        print(f"[FIXED REGISTRY BUILD SCRIPT] {p.relative_to(root)}")
        cmd=["cmd","/c",str(p)] if p.suffix.lower() in {".bat",".cmd"} else [sys.executable,str(p)]
        run(cmd,p.parent,log,env=self.build_env())
        return locate_payload(root,cfg.get("expected_exe_patterns",[]),cfg.get("output_directories",[]),started)

    def build_env(self):
        e=os.environ.copy()
        e.update({
            "CI":"true",
            "PYTHONUTF8":"1",
            "PYTHONIOENCODING":"utf-8",
            "INSIGHTEC_GUIDE_ENABLED":"1" if self.ctx.guide else "0",
            "INSIGHTEC_HUB_VARIANT":self.ctx.hub_variant,
            "INSIGHTEC_RELEASE_MODE":"1",
            "INSIGHTEC_BUILD_STAGE":str(getattr(self.ctx,"build_stage","") or os.getenv("INSIGHTEC_BUILD_STAGE", "")),
        })
        return e
