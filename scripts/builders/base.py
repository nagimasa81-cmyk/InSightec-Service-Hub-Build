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

    def build(self)->tuple[Path,Path]:
        c=self.ctx; root=c.source_root; log=c.log_path; started=time.time()
        for req in detect_requirements(root):
            run([sys.executable,"-m","pip","install","-r",str(req)],req.parent,log)

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
        })
        return e
