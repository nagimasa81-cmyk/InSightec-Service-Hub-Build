from __future__ import annotations
import os, shutil, sys, time
from pathlib import Path
from common.build_common import detect_entry, detect_requirements, locate_payload, run
class BaseBuilder:
    name="base"
    def __init__(self, ctx): self.ctx=ctx
    def build(self)->tuple[Path,Path]:
        c=self.ctx; root=c.source_root; log=c.log_path; started=time.time()
        for req in detect_requirements(root): run([sys.executable,"-m","pip","install","-r",str(req)],root,log)
        cfg=c.build_config; script=cfg.get("build_script") or c.version.get("build_script") or c.module_config.get("build_script")
        if script:
            matches=[p for p in root.rglob(Path(script).name) if p.is_file()]
            if matches:
                p=matches[0]
                cmd=["cmd","/c",str(p)] if p.suffix.lower() in {".bat",".cmd"} else [sys.executable,str(p)]
                run(cmd,p.parent,log,env=self.build_env())
                return locate_payload(root, c.build_config.get("expected_exe_patterns", []), c.build_config.get("output_directories", []), started)
        entry=detect_entry(root,c.entry_point)
        if entry.suffix.lower()==".spec":
            run([sys.executable,"-m","PyInstaller","--noconfirm",str(entry)],entry.parent,log,env=self.build_env())
        elif c.engine=="nuitka": self.nuitka(entry)
        else: self.pyinstaller(entry)
        return locate_payload(root, c.build_config.get("expected_exe_patterns", []), c.build_config.get("output_directories", []), started)
    def build_env(self):
        e=os.environ.copy(); e["INSIGHTEC_RELEASE_MODE"]="1"; e["INSIGHTEC_GUIDE_ENABLED"]="1" if self.ctx.guide else "0"; return e
    def pyinstaller(self,entry):
        run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed","--name",self.ctx.exe_stem,str(entry)],entry.parent,self.ctx.log_path,env=self.build_env())
    def nuitka(self,entry):
        run([sys.executable,"-m","nuitka","--standalone","--enable-plugin=pyside6","--windows-console-mode=disable",f"--output-filename={self.ctx.exe_stem}.exe",str(entry)],entry.parent,self.ctx.log_path,env=self.build_env())
