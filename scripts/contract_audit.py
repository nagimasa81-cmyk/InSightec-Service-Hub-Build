from __future__ import annotations
import argparse, json, re, shutil, sys, tempfile, zipfile
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=json.loads((ROOT/'config/module_registry.json').read_text(encoding='utf-8-sig'))
SKIP={'build','dist','release','.venv','venv','.venv_nuitka','__pycache__'}

@dataclass
class Result:
    module:str; status:str; source_zip:str; contract:str=''; build_script:str=''; entry_point:str=''; runtime:str=''; python:str=''; details:list[str]|None=None

def zips_for(module:str):
    return sorted((ROOT/'Module'/module).glob('*.zip'), key=lambda p:p.stat().st_mtime, reverse=True)

def unwrap(root:Path)->Path:
    visible=[p for p in root.iterdir() if p.name not in {'__MACOSX'}]
    if len(visible)==1 and visible[0].is_dir(): return visible[0]
    return root

def read_text(p:Path)->str:
    for enc in ('utf-8-sig','cp932','utf-8'):
        try:return p.read_text(encoding=enc)
        except Exception:pass
    return p.read_text(encoding='utf-8',errors='replace')

def bat_local_refs(text:str)->set[str]:
    refs=set()
    # Explicit source/config/resource names. Variables are handled separately.
    for m in re.finditer(r'(?i)(?:^|[\s"=])(?!https?://)([^\s"<>|]+\.(?:py|json|txt|ico|png|jpg|jpeg|yaml|yml|toml|spec|ini))(?=$|[\s"<>|])', text):
        s=m.group(1).strip('"').replace('\\','/')
        if '=' in s or '%' in s or '*' in s or s.startswith('-'): continue
        refs.add(s)
    for m in re.finditer(r'(?i)%~dp0([^\s"]+\.py)', text): refs.add(m.group(1).replace('\\','/'))
    # set "VAR=value" and set VAR=value substitutions used as a filename.
    vars={}
    for line in text.splitlines():
        mm=re.match(r'(?i)\s*set\s+"?([A-Za-z_][A-Za-z0-9_]*)=([^"\r\n]+)"?\s*$',line)
        if mm: vars[mm.group(1).upper()]=mm.group(2).strip().strip('"')
    for var,val in vars.items():
        if re.search(rf'%{re.escape(var)}%\.py',text,re.I): refs.add(val+'.py')
        if re.search(rf'%{re.escape(var)}%\.json',text,re.I): refs.add(val+'.json')
    return refs

def audit(module:str)->Result:
    cfg=REG['modules'][module]; runtime=cfg.get('runtime',REG['defaults']['runtime']); py=REG['runtimes'][runtime]['python']
    zs=zips_for(module); d=[]
    if not zs:return Result(module,'FAIL','',runtime=runtime,python=py,details=['SOURCE ZIP missing'])
    z=zs[0]
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'x'
        try:
            with zipfile.ZipFile(z) as zz:
                bad=zz.testzip()
                if bad:d.append(f'ZIP CRC failure: {bad}')
                zz.extractall(out)
        except Exception as e:return Result(module,'FAIL',z.name,runtime=runtime,python=py,details=[f'ZIP error: {e}'])
        root=unwrap(out)
        contracts=[p for p in root.rglob('insightec_build_contract.json') if not any(x in SKIP for x in p.parts)]
        if len(contracts)!=1:
            d.append(f'Expected exactly one contract, found {len(contracts)}')
            return Result(module,'FAIL',z.name,runtime=runtime,python=py,details=d)
        cp=contracts[0]
        try:c=json.loads(cp.read_text(encoding='utf-8-sig'))
        except Exception as e:
            return Result(module,'FAIL',z.name,str(cp.relative_to(root)),runtime=runtime,python=py,details=[f'Contract JSON: {e}'])
        base=cp.parent; build=c.get('build',{}); bat=base/str(build.get('file','')); ep=base/str(c.get('root_marker',''))
        if c.get('module_folder')!=module:d.append(f"contract module_folder={c.get('module_folder')} expected={module}")
        if build.get('mode')!='bat':d.append(f"build mode is not bat: {build.get('mode')}")
        if not bat.is_file():d.append(f'Build BAT missing: {bat.relative_to(root)}')
        if not ep.is_file():d.append(f'Entry point missing: {ep.relative_to(root)}')
        if bat.is_file():
            text=read_text(bat)
            for tok in build.get('forbidden_tokens',[]):
                if tok and tok.lower() in text.lower():d.append(f'Forbidden token in BAT: {tok}')
            if not re.search(r'(?i)(exit\s+/b\s+1|goto\s+ERR|\|\|\s*exit\s+/b)',text):d.append('BAT has no clear non-zero failure exit')
            # Runtime consistency: reject explicit incompatible versions/fallback.
            versions=set(re.findall(r'(?i)(?:py\s+-|version_info\[:2\]\s*==\s*\()\s*3[,.](\d+)',text))
            # also simpler py -3.13 / py -3.14
            versions.update(re.findall(r'(?i)py\s+-3\.(\d+)',text))
            expected_minor=py.split('.')[1]
            incompatible=sorted(v for v in versions if v!=expected_minor)
            if incompatible:d.append(f"BAT references incompatible Python 3.{','.join(incompatible)}; workflow uses {py}")
            # Deletion/output-only references are not required before build.
            input_text='\n'.join(line for line in text.splitlines() if not re.match(r'(?i)\s*(del|rmdir|mkdir|copy|xcopy|echo)\b', line))
            refs=bat_local_refs(input_text)
            for ref in sorted(refs):
                p=(bat.parent/ref).resolve()
                try:p.relative_to(root.resolve())
                except ValueError:
                    d.append(f'BAT reference escapes source: {ref}'); continue
                if not p.exists():d.append(f'BAT referenced file missing: {ref}')
            # Contract entry must actually occur in BAT, directly or via variable.
            if ep.is_file() and ep.name.lower() not in text.lower():
                app=ep.stem
                indirect=''
                for ref in refs:
                    rp=bat.parent/ref
                    if rp.suffix.lower()=='.py' and rp.is_file(): indirect += read_text(rp)
                if not re.search(rf'(?i)set\s+"?(?:APP|MAIN_PY)={re.escape(app)}(?:\.py)?',text) and ep.name.lower() not in indirect.lower():
                    d.append(f'Contract entry point is not referenced by BAT or its launcher: {ep.name}')
        patterns=build.get('expected_exe_patterns',[])
        if not patterns:d.append('expected_exe_patterns is empty')
        if not build.get('output_directories'):d.append('output_directories is empty')
        return Result(module,'PASS' if not d else 'FAIL',z.name,str(cp.relative_to(root)),str(bat.relative_to(root)),str(ep.relative_to(root)),runtime,py,d)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--module',action='append'); ap.add_argument('--all',action='store_true'); ap.add_argument('--report',default='artifacts/contract_audit.json'); args=ap.parse_args()
    scope=REG.get('workflow_selection',{}); modules=[scope.get('hub_module')]+scope.get('standalone_modules',[]) if args.all or not args.module else args.module
    modules=[m for m in modules if m]
    results=[audit(m) for m in modules]
    for r in results:
        print(f"[{r.status}] {r.module}: {r.build_script} -> {r.entry_point} / Python {r.python}")
        for x in r.details or []:print('  -',x)
    report=ROOT/args.report; report.parent.mkdir(parents=True,exist_ok=True); report.write_text(json.dumps({'results':[asdict(x) for x in results]},indent=2,ensure_ascii=False),encoding='utf-8')
    if any(r.status!='PASS' for r in results):sys.exit(1)
if __name__=='__main__':main()
