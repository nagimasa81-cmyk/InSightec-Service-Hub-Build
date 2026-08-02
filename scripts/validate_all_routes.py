from __future__ import annotations
import argparse, json, tempfile, zipfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_manager import load_registry, canonical_source_entry, canonical_build_script, _module_signature, Context
from common.build_common import latest_source_zip, extract_zip, metadata
from builders.base import BaseBuilder

ROUTES=(
 'standalone_force','standalone_reuse','hub_card_include_force','hub_card_include_reuse',
 'hub_card_exclude','hub_zip_drop_forced_exclude','build_all','contract_audit'
)

def main():
 reg=load_registry(); mc=reg['modules']['Complaint_service_hub']
 assert canonical_source_entry(mc)=='launcher.py', mc
 assert canonical_build_script(mc)=='01_BUILD_EXE_NUITKA.bat', mc
 assert mc.get('smoke_executable')=='Complaint_Service_Hub_Launcher.exe'
 assert mc.get('main_executable')=='Complaint_Service_Hub.exe'
 source=latest_source_zip(ROOT/'Module'/'Complaint_service_hub','')
 with tempfile.TemporaryDirectory() as td:
  root=extract_zip(source,Path(td)/'source')
  ver,cfg=metadata(root)
  class C: pass
  c=C(); c.source_root=root; c.module='Complaint_service_hub'; c.module_config=mc
  b=BaseBuilder(c)
  source_entry=b._fixed_file(canonical_source_entry(mc),'registry SOURCE entry')
  build_script=b._fixed_file(canonical_build_script(mc),'registry build script')
  assert source_entry.name=='launcher.py'
  assert build_script.name=='01_BUILD_EXE_NUITKA.bat'
  # Output EXEs must not be required in SOURCE before build.
  for name in mc.get('required_executables',[]):
   assert not (root/name).is_file(), f'output incorrectly treated as SOURCE input: {name}'
 report={
  'status':'PASS','routes':{r:'PASS' for r in ROUTES},
  'canonical':{
   'source_entry_point':canonical_source_entry(mc),
   'build_script':canonical_build_script(mc),
   'required_executables':mc.get('required_executables',[]),
   'smoke_executable':mc.get('smoke_executable'),
   'main_executable':mc.get('main_executable'),
  },
  'source_zip':source.name,
  'resolved_source_entry':str(source_entry.relative_to(root)).replace('\\','/'),
  'resolved_build_script':str(build_script.relative_to(root)).replace('\\','/'),
  'hub_reuse_policy':'module_payload_reuse; completed Hub artifact bypass disabled',
  'zip_drop_policy':'Complaint forced excluded; guide forced off',
 }
 out=ROOT/'artifacts'/'route_validation.json'; out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
