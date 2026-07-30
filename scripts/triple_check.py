from __future__ import annotations
import argparse, json, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common.build_common import latest_source_zip, read_json

def inspect_zip(path:Path, configured_entry:str="", configured_build:str=""):
 with zipfile.ZipFile(path) as z:
  names=[n for n in z.namelist() if not n.endswith('/')]
 low={n.lower():n for n in names}
 def ends(s): return [n for n in names if n.lower().endswith(s)]
 return {
  'source_zip': True,
  'version_json': bool(ends('version.json')),
  'build_config_json': bool(ends('build_config.json')),
  'requirements': bool([n for n in names if Path(n).name.lower().startswith('requirements') and n.lower().endswith('.txt')]) or bool(ends('pyproject.toml')),
  'entry_point': bool([n for n in names if configured_entry and Path(n).name.lower()==Path(configured_entry).name.lower()]) or bool([n for n in names if Path(n).name.lower() in {'main.py','app.py','launcher.py','run.py','start.py','hub_app.py'}]) or bool([n for n in names if n.lower().endswith('.spec')]),
  'build_script': bool([n for n in names if configured_build and Path(n).name.lower()==Path(configured_build).name.lower()]),
  'spec': bool([n for n in names if n.lower().endswith('.spec')]),
  'zip_drop_implementation': any('auto_dataset_analyzer' in n.lower() for n in names) or any(Path(n).name == 'InSightecServiceHub.py' for n in names),
  'build_contract': bool(ends('insightec_build_contract.json')),
 }
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--module',default=''); ap.add_argument('--artifact',default=''); a=ap.parse_args()
 reg=read_json(ROOT/'config/module_registry.json'); mods=[a.module] if a.module else [reg['workflow_selection']['hub_module'], *reg['workflow_selection']['standalone_modules']]
 report=[]
 for m in mods:
  mc=reg.get('modules',{}).get(m,{})
  try:
   z=latest_source_zip(ROOT/'Module'/m); checks=inspect_zip(z, mc.get('entry_point',''), mc.get('build_script',''))
   checks.update(module=m,builder=bool(mc.get('builder')),runtime=bool(mc.get('runtime')),registry_entry=bool(mc.get('entry_point')))
  except Exception as e: checks={'module':m,'source_zip':False,'error':str(e)}
  report.append(checks)
 if a.artifact:
  p=Path(a.artifact); report.append({'artifact':str(p),'artifact_exists':p.is_file(),'sha256_exists':p.with_suffix(p.suffix+'.sha256').is_file() if p.suffix else False})
 out=ROOT/'artifacts'/'triple_check.json'; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 for r in report: print(r)
 # Metadata absence is reported, but legacy modules can use Registry fallback.
 if any(not r.get('source_zip',True) for r in report): raise SystemExit(1)
if __name__=='__main__':main()
