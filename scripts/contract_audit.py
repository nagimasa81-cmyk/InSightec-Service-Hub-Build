from __future__ import annotations
import argparse, json, re, sys, tempfile, zipfile
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.build_common import latest_source_zip

ROOT=Path(__file__).resolve().parents[1]
REG=json.loads((ROOT/'config/module_registry.json').read_text(encoding='utf-8-sig'))
SKIP={'build','dist','release','.venv','venv','.venv_nuitka','__pycache__'}

@dataclass
class Result:
    module:str; status:str; source_zip:str; contract:str=''; build_script:str=''; entry_point:str=''; runtime:str=''; python:str=''; details:list[str]|None=None

def source_zip_for(module:str)->Path:
    module_dir=ROOT/'Module'/module
    return latest_source_zip(module_dir)

def unwrap(root:Path)->Path:
    visible=[p for p in root.iterdir() if p.name not in {'__MACOSX'}]
    while len(visible)==1 and visible[0].is_dir():
        root=visible[0]
        visible=[p for p in root.iterdir() if p.name not in {'__MACOSX'}]
    return root

def read_text(p:Path)->str:
    for enc in ('utf-8-sig','cp932','utf-8'):
        try:return p.read_text(encoding=enc)
        except Exception:pass
    return p.read_text(encoding='utf-8',errors='replace')

def bat_local_refs(text:str)->set[str]:
    refs=set()
    # Output redirection targets are generated files, not source dependencies.
    scan_text=re.sub(r'(?im)(?:^|\s)(?:1?>|2>|>>)[ \t]*"?[^\s"&|<>]+', ' ', text)
    for m in re.finditer(r'(?i)(?:^|[\s"=])(?!https?://)([^\s"<>|]+\.(?:py|json|txt|ico|png|jpg|jpeg|yaml|yml|toml|spec|ini))(?=$|[\s"<>|])', scan_text):
        s=m.group(1).strip('"').replace('\\','/')
        if '=' in s or '%' in s or '*' in s or s.startswith('-'): continue
        refs.add(s)
    for m in re.finditer(r'(?i)%~dp0([^\s"]+\.py)', text): refs.add(m.group(1).replace('\\','/'))
    vars={}
    for line in text.splitlines():
        mm=re.match(r'(?i)\s*set\s+"?([A-Za-z_][A-Za-z0-9_]*)=([^"\r\n]+)"?\s*$',line)
        if mm: vars[mm.group(1).upper()]=mm.group(2).strip().strip('"')
    for var,val in vars.items():
        if re.search(rf'%{re.escape(var)}%\.py',text,re.I): refs.add(val+'.py')
        if re.search(rf'%{re.escape(var)}%\.json',text,re.I): refs.add(val+'.json')
    return refs

def hub_legacy_contract(root:Path):
    """Explicit Service Hub rule; this is not generic fallback."""
    py=[p for p in root.rglob('Build_Hub_EXE.py') if not any(x in SKIP for x in p.parts)]
    bats=[p for p in root.rglob('Build_Hub_EXE_PyInstaller.bat') if not any(x in SKIP for x in p.parts)]
    entries=[p for p in root.rglob('InSightecServiceHub.py') if not any(x in SKIP for x in p.parts)]
    if len(py)==1 and len(bats)==1 and len(entries)==1:
        return bats[0], entries[0], 'Service Hub explicit Build_Hub_EXE.py rule (contract file not required)'
    return None


def complaint_legacy_contract(root:Path):
    """Explicit Complaint Service Hub rule for legacy sources without contract JSON."""
    bats=[p for p in root.rglob('01_BUILD_EXE_NUITKA.bat') if not any(x in SKIP for x in p.parts)]
    launchers=[p for p in root.rglob('launcher.py') if not any(x in SKIP for x in p.parts)]
    hubs=[p for p in root.rglob('hub_app.py') if not any(x in SKIP for x in p.parts)]
    updaters=[p for p in root.rglob('updater.py') if not any(x in SKIP for x in p.parts)]
    if len(bats)==1 and len(launchers)==1 and len(hubs)==1 and len(updaters)==1:
        build={
            'expected_exe_patterns':[
                'Complaint_Service_Hub_Launcher.exe',
                'Complaint_Service_Hub.exe',
                'Complaint_Service_Hub_Updater.exe',
            ],
            'output_directories':['dist/Complaint_Service_Hub'],
            'forbidden_tokens':[],
        }
        return bats[0], launchers[0], build, 'Complaint explicit legacy Nuitka rule (contract file not required)'
    return None



def water_legacy_contract(root:Path):
    """Explicit Water System Analyzer rule for legacy sources without contract JSON."""
    bats=[p for p in root.rglob('build_exe.bat') if not any(x in SKIP for x in p.parts)]
    entries=[p for p in root.rglob('WaterSystemAnalyzer_Ver42_StableIntegrated.py') if not any(x in SKIP for x in p.parts)]
    requirements=[p for p in root.rglob('requirements_py313_pyside6_nuitka.txt') if not any(x in SKIP for x in p.parts)]
    if len(bats)==1 and len(entries)==1 and len(requirements)==1:
        build={
            'expected_exe_patterns':['WaterSystemAnalyzer_Ver42.exe'],
            'output_directories':['dist/WaterSystemAnalyzer_Ver42'],
            'forbidden_tokens':[],
        }
        return bats[0], entries[0], build, 'Water System Analyzer explicit legacy Nuitka rule (contract file not required)'
    return None

def discover_manifest_modules(*, supports_hub:bool|None=None)->list[str]:
    """Discover registered modules from Module/*/module.json without a fixed count."""
    found=[]
    module_root=ROOT/'Module'
    if not module_root.is_dir():
        return found
    for manifest in sorted(module_root.glob('*/module.json'), key=lambda x:x.parent.name.lower()):
        try:
            data=json.loads(manifest.read_text(encoding='utf-8-sig'))
        except Exception:
            continue
        module_id=str(data.get('id') or manifest.parent.name).strip()
        if not module_id or module_id not in REG.get('modules',{}):
            continue
        if supports_hub is not None and bool(data.get('supports_hub',False)) is not supports_hub:
            continue
        found.append(module_id)
    return found

def audit(module:str)->Result:
    cfg=REG['modules'][module]; runtime=cfg.get('runtime',REG['defaults']['runtime']); py=REG['runtimes'][runtime]['python']; d=[]
    try:z=source_zip_for(module)
    except Exception as e:return Result(module,'FAIL','',runtime=runtime,python=py,details=[str(e)])
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
        contract_label=''
        if len(contracts)==1:
            cp=contracts[0]
            try:c=json.loads(cp.read_text(encoding='utf-8-sig'))
            except Exception as e:return Result(module,'FAIL',z.name,str(cp.relative_to(root)),runtime=runtime,python=py,details=[f'Contract JSON: {e}'])
            base=cp.parent; build=c.get('build',{}); bat=base/str(build.get('file','')); ep=base/str(c.get('root_marker',''))
            contract_label=str(cp.relative_to(root))
            if c.get('module_folder')!=module:d.append(f"contract module_folder={c.get('module_folder')} expected={module}")
            if build.get('mode')!='bat':d.append(f"build mode is not bat: {build.get('mode')}")
        elif len(contracts)==0 and module=='InSightec_Service_hub':
            legacy=hub_legacy_contract(root)
            if not legacy:
                return Result(module,'FAIL',z.name,runtime=runtime,python=py,details=['Service Hub contract missing and explicit Build_Hub_EXE.py layout is incomplete'])
            bat,ep,note=legacy; build={'expected_exe_patterns':['*.exe'],'output_directories':['dist','release','build']}; contract_label='SERVICE_HUB_EXPLICIT_RULE'; d.append(note)
        elif len(contracts)==0 and module=='Complaint_service_hub':
            legacy=complaint_legacy_contract(root)
            if not legacy:
                return Result(module,'FAIL',z.name,runtime=runtime,python=py,details=['Complaint contract missing and explicit legacy Nuitka layout is incomplete'])
            bat,ep,build,note=legacy; contract_label='COMPLAINT_EXPLICIT_RULE'; d.append(note)
        elif len(contracts)==0 and module=='Water_system_analyzer':
            legacy=water_legacy_contract(root)
            if not legacy:
                return Result(module,'FAIL',z.name,runtime=runtime,python=py,details=['Water System Analyzer contract missing and explicit legacy Nuitka layout is incomplete'])
            bat,ep,build,note=legacy; contract_label='WATER_EXPLICIT_RULE'; d.append(note)
        else:
            return Result(module,'FAIL',z.name,runtime=runtime,python=py,details=[f'Expected exactly one contract, found {len(contracts)}'])

        if not bat.is_file():d.append(f'Build BAT missing: {bat.relative_to(root)}')
        if not ep.is_file():d.append(f'Entry point missing: {ep.relative_to(root)}')
        if bat.is_file():
            text=read_text(bat)
            for tok in build.get('forbidden_tokens',[]):
                if tok and tok.lower() in text.lower():d.append(f'Forbidden token in BAT: {tok}')
            if not re.search(r'(?i)(exit\s+/b\s+1|goto\s+ERR|\|\|\s*exit\s+/b)',text):d.append('BAT has no clear non-zero failure exit')
            versions=set(re.findall(r'(?i)(?:py\s+-|version_info\[:2\]\s*==\s*\()\s*3[,.](\d+)',text))
            versions.update(re.findall(r'(?i)py\s+-3\.(\d+)',text))
            expected_minor=py.split('.')[1]; incompatible=sorted(v for v in versions if v!=expected_minor)
            if incompatible:d.append(f"BAT references incompatible Python 3.{','.join(incompatible)}; workflow uses {py}")
            input_text='\n'.join(line for line in text.splitlines() if not re.match(r'(?i)\s*(del|rmdir|mkdir|copy|xcopy|echo)\b', line))
            refs=bat_local_refs(input_text)
            for ref in sorted(refs):
                p=(bat.parent/ref).resolve()
                try:p.relative_to(root.resolve())
                except ValueError:d.append(f'BAT reference escapes source: {ref}'); continue
                if not p.exists():d.append(f'BAT referenced file missing: {ref}')
            if ep.is_file() and ep.name.lower() not in text.lower():
                app=ep.stem; indirect=''
                for ref in refs:
                    rp=bat.parent/ref
                    if rp.suffix.lower()=='.py' and rp.is_file(): indirect += read_text(rp)
                if not re.search(rf'(?i)set\s+"?(?:APP|MAIN_PY)={re.escape(app)}(?:\.py)?',text) and ep.name.lower() not in indirect.lower():
                    d.append(f'Contract entry point is not referenced by BAT or its launcher: {ep.name}')
        if not build.get('expected_exe_patterns'):d.append('expected_exe_patterns is empty')
        if not build.get('output_directories'):d.append('output_directories is empty')
        hard=[x for x in d if not (x.startswith('Service Hub explicit') or x.startswith('Complaint explicit legacy') or x.startswith('Water System Analyzer explicit legacy'))]
        return Result(module,'PASS' if not hard else 'FAIL',z.name,contract_label,str(bat.relative_to(root)),str(ep.relative_to(root)),runtime,py,d)

def selected_modules(target:str, selected:str, exclude_sonication:bool=False, exclude_complaint:bool=False)->list[str]:
    scope=REG.get('workflow_selection',{})
    if target=='module': return [selected]
    hub_module=scope['hub_module']
    if target=='service_hub':
        discovered=discover_manifest_modules(supports_hub=True)
        # Compatibility fallback for older repositories that do not yet carry manifests.
        items=discovered or list(scope.get('service_hub_modules',[]))
        items=[hub_module, *items]
        return [m for m in items if not (exclude_sonication and m=='Soni') and not (exclude_complaint and m=='Complaint_service_hub')]
    if target=='all':
        discovered=discover_manifest_modules(supports_hub=None)
        items=[m for m in discovered if m != hub_module] or list(scope.get('standalone_modules',[]))
        return [hub_module, *items]
    raise ValueError(f'Unknown target: {target}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--module',action='append'); ap.add_argument('--target',choices=['module','service_hub','all']); ap.add_argument('--selected-module',default=''); ap.add_argument('--exclude-sonication',action='store_true'); ap.add_argument('--exclude-complaint',action='store_true'); ap.add_argument('--all',action='store_true'); ap.add_argument('--report',default='artifacts/contract_audit.json'); args=ap.parse_args()
    if args.module: modules=args.module
    elif args.target: modules=selected_modules(args.target,args.selected_module,args.exclude_sonication,args.exclude_complaint)
    elif args.all: modules=selected_modules('all','',args.exclude_sonication,args.exclude_complaint)
    else: raise SystemExit('Specify --module, --target, or --all')
    modules=list(dict.fromkeys(m for m in modules if m))
    results=[audit(m) for m in modules]
    for r in results:
        print(f"[{r.status}] {r.module}: {r.source_zip} | {r.build_script} -> {r.entry_point} / Python {r.python}")
        for x in r.details or []:print('  -',x)
    report=ROOT/args.report; report.parent.mkdir(parents=True,exist_ok=True); report.write_text(json.dumps({'scope':modules,'results':[asdict(x) for x in results]},indent=2,ensure_ascii=False),encoding='utf-8')
    if any(r.status!='PASS' for r in results):sys.exit(1)
if __name__=='__main__':main()
