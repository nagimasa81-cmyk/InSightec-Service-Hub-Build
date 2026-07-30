from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common.build_common import latest_source_zip, read_json, extract_zip, metadata, detect_requirements

SKIP_DIRS = {".git", ".venv", "venv", "site-packages", "build", "dist", "dist_nuitka", "__pycache__"}
WINDOWS_BAD_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}

@dataclass
class Check:
    name: str
    status: str
    detail: str


def add(checks: list[Check], name: str, ok: bool, detail: str, warning: bool=False) -> None:
    checks.append(Check(name, "WARN" if warning and not ok else ("PASS" if ok else "FAIL"), detail))


def exact_matches(root: Path, configured: str) -> list[Path]:
    if not configured:
        return []
    candidate=(root/configured).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return []
    return [candidate] if candidate.is_file() else []


def validate_json_files(root: Path, checks: list[Check]) -> None:
    candidates = [p for p in root.rglob("*.json") if p.is_file() and not any(x in SKIP_DIRS for x in p.parts)]
    failures=[]
    for p in candidates:
        try:
            json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as e:
            failures.append(f"{p.relative_to(root)}: {e}")
    add(checks, "JSON parse", not failures, f"{len(candidates)} JSON files checked" if not failures else "; ".join(failures[:10]))


def validate_python_syntax(root: Path, checks: list[Check]) -> None:
    files=[p for p in root.rglob("*.py") if p.is_file() and not any(x in SKIP_DIRS for x in p.parts)]
    failures=[]
    for p in files:
        try:
            ast.parse(p.read_text(encoding="utf-8-sig", errors="strict"), filename=str(p))
        except UnicodeDecodeError:
            try:
                ast.parse(p.read_text(encoding="cp932", errors="strict"), filename=str(p))
            except Exception as e:
                failures.append(f"{p.relative_to(root)}: {e}")
        except SyntaxError as e:
            failures.append(f"{p.relative_to(root)}:{e.lineno}: {e.msg}")
        except Exception as e:
            failures.append(f"{p.relative_to(root)}: {e}")
    add(checks, "Python syntax", not failures, f"{len(files)} Python files parsed" if not failures else "; ".join(failures[:15]))


def validate_requirements(root: Path, checks: list[Check]) -> None:
    reqs=detect_requirements(root)
    bad=[]
    remote=re.compile(r"(^|\s)(file:|https?://|git\+|-[ec]\s|--index-url|--extra-index-url)", re.I)
    for p in reqs:
        for i,line in enumerate(p.read_text(encoding="utf-8-sig",errors="replace").splitlines(),1):
            s=line.strip()
            if not s or s.startswith("#"):
                continue
            if s.lower().startswith("-r "):
                included=(p.parent/s[3:].strip()).resolve()
                if not included.is_file(): bad.append(f"{p.name}:{i}: included requirements missing: {s[3:].strip()}")
                continue
            if "\\" in s and not s.startswith("--"):
                bad.append(f"{p.name}:{i}: local Windows path: {s}")
            elif remote.search(s):
                bad.append(f"{p.name}:{i}: non-reproducible dependency: {s}")
    add(checks, "Requirements safety", not bad, f"{len(reqs)} requirements files checked" if not bad else "; ".join(bad[:12]))


def validate_windows_paths(root: Path, checks: list[Check]) -> None:
    bad=[]; long=[]
    for p in root.rglob("*"):
        rel=p.relative_to(root)
        for part in rel.parts:
            stem=Path(part).stem.upper()
            if stem in WINDOWS_BAD_NAMES or part.endswith(" ") or part.endswith(".") or any(c in part for c in '<>:"|?*'):
                bad.append(str(rel)); break
        # GitHub workspace + extraction/build prefixes consume substantial path length.
        if len(str(rel)) > 170:
            long.append(f"{len(str(rel))}:{rel}")
    add(checks, "Windows filename safety", not bad, "No invalid Windows names" if not bad else "; ".join(bad[:10]))
    add(checks, "Windows path length", not long, "All relative paths <= 170 chars" if not long else "; ".join(long[:10]))


def validate_build_script(root: Path, script: str, checks: list[Check]) -> None:
    matches=exact_matches(root, script)
    add(checks, "Build script", len(matches)==1, f"{matches[0].relative_to(root)}" if len(matches)==1 else f"Expected exactly 1 '{script}', found {len(matches)}")
    if len(matches)!=1:
        return
    p=matches[0]
    text=p.read_text(encoding="utf-8-sig",errors="replace")
    # Catch common unresolved placeholders and hard-coded local absolute paths.
    unresolved=re.findall(r"(?i)(?:TODO|CHANGE_ME|YOUR_PATH|C:\\Users\\[^%])", text)
    add(checks, "Build script portability", not unresolved, "No unresolved placeholder or user-specific path" if not unresolved else "Potential placeholder/user path detected")
    has_error_guard = bool(re.search(r"(?i)(errorlevel|\|\|\s*(exit|goto)|if\s+not\s+exist|exit\s+/b)", text))
    add(checks, "Build script failure guard", has_error_guard, "Error handling detected" if has_error_guard else "No explicit errorlevel/output guard detected", warning=True)


def inspect(module: str, source_name: str="", guide: bool=False, hub_variant: str="card_launcher") -> tuple[list[Check], dict]:
    registry=read_json(ROOT/"config/module_registry.json")
    checks=[]
    add(checks, "Registry JSON", bool(registry.get("modules")), "Registry loaded")
    mc=registry.get("modules",{}).get(module)
    add(checks, "Registry module", mc is not None, module)
    if not mc:
        return checks, {}
    module_dir=ROOT/"Module"/module
    add(checks, "Module directory", module_dir.is_dir(), str(module_dir))
    try:
        source=latest_source_zip(module_dir, source_name)
    except Exception as e:
        add(checks, "SOURCE ZIP", False, str(e)); return checks, {}
    add(checks, "SOURCE ZIP", source.is_file() and source.stat().st_size>0, f"{source.name} ({source.stat().st_size:,} bytes)")
    try:
        with zipfile.ZipFile(source) as z:
            bad=z.testzip()
            names=z.namelist()
        add(checks, "ZIP CRC", bad is None, "CRC OK" if bad is None else f"Corrupt member: {bad}")
        add(checks, "ZIP content", len(names)>2, f"{len(names)} entries")
    except Exception as e:
        add(checks, "ZIP CRC", False, str(e)); return checks, {}
    tmp=ROOT/".preflight"/module/"source"
    try:
        extracted=extract_zip(source,tmp)
    except Exception as e:
        add(checks, "ZIP extraction", False, str(e)); return checks, {}
    add(checks, "ZIP extraction", True, str(extracted.relative_to(ROOT)))
    version,cfg=metadata(extracted)
    entry=str(cfg.get("entrypoint") or cfg.get("entry_point") or version.get("entry_point") or mc.get("entry_point") or "")
    script=str(cfg.get("build_script") or version.get("build_script") or mc.get("build_script") or "")
    entry_matches=exact_matches(extracted,entry)
    add(checks, "Entry point exact", len(entry_matches)==1, f"{entry_matches[0].relative_to(extracted)}" if len(entry_matches)==1 else f"Expected exactly 1 '{entry}', found {len(entry_matches)}")
    if len(entry_matches)==1:
        ep=entry_matches[0]
        try:
            ast.parse(ep.read_text(encoding="utf-8-sig",errors="strict"),filename=str(ep))
            add(checks,"Entry point syntax",True,str(ep.relative_to(extracted)))
        except Exception as e:
            add(checks,"Entry point syntax",False,str(e))
    validate_build_script(extracted,script,checks)
    validate_json_files(extracted,checks)
    validate_python_syntax(extracted,checks)
    validate_requirements(extracted,checks)
    validate_windows_paths(extracted,checks)
    icon=str(mc.get("icon") or "")
    icon_matches=exact_matches(extracted,icon) if icon else []
    add(checks,"Icon", bool(icon_matches) or not icon, f"{len(icon_matches)} match(es) for {icon}" if icon else "Not configured", warning=True)
    runtime=str(cfg.get("runtime") or version.get("runtime") or mc.get("runtime") or registry.get("defaults",{}).get("runtime"))
    runtime_cfg=registry.get("runtimes",{}).get(runtime)
    add(checks,"Runtime", runtime_cfg is not None, f"{runtime} / Python {runtime_cfg.get('python') if runtime_cfg else '?'}")
    if module==registry.get("workflow_selection",{}).get("hub_module"):
        text="\n".join(p.read_text(encoding="utf-8",errors="ignore") for p in extracted.rglob("*.py") if p.is_file())
        if hub_variant=="zip_drop":
            implemented=("Auto Dataset Analyzer" in text or "auto_dataset_analyzer" in text.lower()) and ("drop" in text.lower())
            add(checks,"Hub ZIP-drop implementation",implemented,"ZIP/drop analyzer symbols detected" if implemented else "ZIP-drop implementation not detected")
        guide_symbols=("guide" in text.lower() or "tour" in text.lower())
        add(checks,"Hub guide implementation", guide_symbols or not guide, "Guide/tour symbols detected" if guide_symbols else "Guide disabled", warning=not guide)
    free=shutil.disk_usage(ROOT).free
    add(checks,"Free disk",free>=8*1024**3,f"{free/1024**3:.1f} GiB free; minimum 8 GiB")
    meta={"module":module,"source_zip":source.name,"entry_point":entry,"build_script":script,"runtime":runtime,"guide":guide,"hub_variant":hub_variant,"version":version}
    return checks,meta


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--module",required=True)
    ap.add_argument("--source-zip",default="")
    ap.add_argument("--guide",action="store_true")
    ap.add_argument("--hub-variant",default="card_launcher")
    ap.add_argument("--report",default="")
    args=ap.parse_args()
    checks,meta=inspect(args.module,args.source_zip,args.guide,args.hub_variant)
    for c in checks:
        print(f"[{c.status}] {c.name}: {c.detail}")
    report={"metadata":meta,"checks":[asdict(c) for c in checks]}
    out=Path(args.report) if args.report else ROOT/"artifacts"/"preflight.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    failures=[c for c in checks if c.status=="FAIL"]
    if failures:
        print(f"PREFLIGHT FAILED: {len(failures)} blocking issue(s)")
        raise SystemExit(2)
    print("PREFLIGHT PASSED")

if __name__=="__main__":
    main()
