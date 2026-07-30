from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

def read_json(path: Path) -> dict:
    try: return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception: return {}

def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def latest_source_zip(module_dir: Path, exact: str="") -> Path:
    """Return the one authoritative SOURCE ZIP for a module.

    No newest-file selection, no Registry filename fallback, and no automatic
    substitution are allowed. An explicit name may be supplied by an internal
    caller, otherwise the module directory must contain exactly one SOURCE ZIP.
    """
    if exact:
        p=module_dir/exact
        if not p.is_file():
            raise FileNotFoundError(f"Exact SOURCE ZIP not found: {p}")
        return p
    source_zips=sorted(
        [p for p in module_dir.glob("*.zip") if "SOURCE" in p.name.upper()],
        key=lambda p:p.name.lower(),
    )
    if len(source_zips)!=1:
        names=", ".join(p.name for p in source_zips) or "none"
        raise RuntimeError(
            f"Expected exactly one SOURCE ZIP in {module_dir}; found {len(source_zips)}: {names}"
        )
    return source_zips[0]

def extract_zip(source: Path, destination: Path) -> Path:
    if destination.exists(): shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(source) as z: z.extractall(destination)
    children=[p for p in destination.iterdir() if p.name not in {"__MACOSX"}]
    while len(children)==1 and children[0].is_dir():
        destination=children[0]; children=[p for p in destination.iterdir() if p.name!="__MACOSX"]
    return destination

def find_files(root: Path, names: tuple[str,...]) -> list[Path]:
    bad={"build","dist","dist_nuitka",".venv","venv","site-packages","__pycache__"}
    return [p for p in root.rglob("*") if p.is_file() and p.name.lower() in names and not any(x in bad for x in p.parts)]

def metadata(root: Path) -> tuple[dict,dict]:
    versions=find_files(root,("version.json",)); configs=find_files(root,("build_config.json",))
    version=read_json(versions[0]) if versions else {}
    config=read_json(configs[0]) if configs else {}
    contracts=find_files(root,("insightec_build_contract.json",))
    if len(contracts) > 1:
        raise RuntimeError("Multiple insightec_build_contract.json files found; fixed build contract must be unique: " + ", ".join(str(p.relative_to(root)) for p in contracts))
    if contracts:
        contract_path=contracts[0]
        contract=read_json(contract_path)
        build=contract.get("build", {}) if isinstance(contract, dict) else {}
        contract_dir=contract_path.parent
        def rel_from_root(name: str) -> str:
            if not name: return ""
            return str((contract_dir/name).relative_to(root)).replace("\\", "/")
        config["entry_point"] = rel_from_root(str(contract.get("root_marker", "")))
        config["build_script"] = rel_from_root(str(build.get("file", "")))
        config["expected_exe_patterns"] = build.get("expected_exe_patterns", [])
        config["output_directories"] = [rel_from_root(str(x)) for x in build.get("output_directories", [])]
        config["build_contract_path"] = str(contract_path.relative_to(root)).replace("\\", "/")
        config["strict_contract"] = True
    return version, config

def detect_requirements(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("requirements*.txt") if p.is_file() and "site-packages" not in p.parts], key=lambda p:(len(p.parts),p.name))

def detect_entry(root: Path, configured: str="") -> Path:
    if configured:
        direct=root/configured
        if direct.is_file(): return direct
        matches=[p for p in root.rglob(Path(configured).name) if p.is_file()]
        if len(matches)==1: return matches[0]
    specs=sorted(root.rglob("*.spec"), key=lambda p:(len(p.parts),p.name))
    if specs: return specs[0]
    for name in ("main.py","app.py","launcher.py","run.py","start.py","hub_app.py"):
        found=sorted(root.rglob(name), key=lambda p:(len(p.parts),p.as_posix()))
        if found: return found[0]
    candidates=[]
    for p in root.rglob("*.py"):
        try: text=p.read_text(encoding="utf-8",errors="ignore")
        except: continue
        score=(100 if "__main__" in text else 0)+(60 if "QApplication" in text else 0)+(40 if "def main(" in text else 0)
        candidates.append((score,-len(p.parts),p))
    if candidates and max(candidates)[0]>0: return max(candidates)[2]
    raise FileNotFoundError("Entry point/spec not detected")

def run(cmd:list[str], cwd:Path, log:Path, env:dict|None=None):
    log.parent.mkdir(parents=True,exist_ok=True)
    print("[RUN]", subprocess.list2cmdline(cmd), flush=True)
    with log.open("a",encoding="utf-8",errors="replace") as f:
        p=subprocess.Popen(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",env=env)
        assert p.stdout
        for line in p.stdout: print(line,end=""); f.write(line)
        rc=p.wait()
    if rc: raise RuntimeError(f"Command failed ({rc}): {cmd}")

def locate_payload(root:Path, expected_patterns:list[str]|None=None, output_directories:list[str]|None=None, not_before:float=0)->tuple[Path,Path]:
    excluded=(".venv","venv","site-packages","__pycache__")
    search_roots=[]
    for raw in output_directories or []:
        candidate=root/raw
        if candidate.is_dir(): search_roots.append(candidate)
    if not search_roots: search_roots=[root]
    exes=[]
    for base in search_roots:
        for p in base.rglob("*.exe"):
            if not p.is_file() or any(x in p.parts for x in excluded): continue
            if not_before and p.stat().st_mtime < not_before-2: continue
            exes.append(p)
    patterns=[x.lower() for x in (expected_patterns or []) if x]
    if patterns:
        matched=[]
        import fnmatch
        for p in exes:
            rel=str(p.relative_to(root)).replace("\\","/").lower()
            if any(fnmatch.fnmatch(rel,pat.lower()) or fnmatch.fnmatch(p.name.lower(),pat.lower()) for pat in patterns): matched.append(p)
        if matched: exes=matched
    if not exes: raise FileNotFoundError("A newly generated EXE was not found in the expected output")
    exe=max(exes,key=lambda p:(p.stat().st_size,p.stat().st_mtime))
    if exe.stat().st_size < 100*1024: raise RuntimeError(f"Generated EXE is unexpectedly small: {exe} ({exe.stat().st_size} bytes)")
    return exe.parent,exe

def verify_payload(payload:Path, exe:Path, source_root:Path)->dict:
    if not exe.is_file(): raise FileNotFoundError(f"EXE missing: {exe}")
    if exe.stat().st_size < 100*1024: raise RuntimeError(f"EXE too small: {exe.stat().st_size} bytes")
    py_text=""
    for p in source_root.rglob("*.py"):
        if any(x in p.parts for x in (".venv","venv","site-packages","build","dist","__pycache__")): continue
        try: py_text += p.read_text(encoding="utf-8",errors="ignore")[:200000]
        except Exception: pass
    qt_app=any(token in py_text for token in ("PySide6","PyQt6","PySide2","PyQt5"))
    dlls=list(payload.rglob("*.dll"))
    qwindows=[p for p in payload.rglob("qwindows.dll")]
    # One-file executables legitimately have no side DLLs. For directory payloads, Qt platforms must be present.
    sibling_files=[p for p in payload.iterdir() if p.is_file()] if payload.is_dir() else []
    directory_bundle=len(sibling_files)>1 or bool(dlls)
    if qt_app and directory_bundle and not qwindows:
        raise RuntimeError("Qt application payload is missing platforms/qwindows.dll")
    return {"exe_size":exe.stat().st_size,"dll_count":len(dlls),"qt_app":qt_app,"qwindows":len(qwindows),"directory_bundle":directory_bundle}

def smoke_test_exe(exe:Path, log:Path, seconds:int=12)->dict:
    if os.name != "nt": return {"status":"skipped_non_windows"}
    env=os.environ.copy(); env.setdefault("QT_LOGGING_RULES","*.debug=false")
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open("a",encoding="utf-8",errors="replace") as f:
        f.write(f"\n[SMOKE] launching {exe}\n")
        creationflags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
        p=subprocess.Popen([str(exe)],cwd=exe.parent,stdout=f,stderr=subprocess.STDOUT,env=env,creationflags=creationflags)
        try:
            rc=p.wait(timeout=seconds)
            if rc != 0: raise RuntimeError(f"EXE exited during smoke test with code {rc}")
            return {"status":"exited_cleanly","exit_code":rc,"seconds":seconds}
        except subprocess.TimeoutExpired:
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill()
            return {"status":"running","seconds":seconds}

def copy_payload(payload:Path,dest:Path):
    if dest.exists(): shutil.rmtree(dest,ignore_errors=True)
    shutil.copytree(payload,dest)

def zip_dir(source:Path,target:Path):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): target.unlink()
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in source.rglob("*"):
            if p.is_file(): z.write(p,p.relative_to(source))
