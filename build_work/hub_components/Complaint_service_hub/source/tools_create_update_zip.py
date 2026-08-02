from __future__ import annotations
import sys, zipfile, datetime, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
kind=(sys.argv[1] if len(sys.argv)>1 else 'master').lower()
ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
if kind=='program':
    out=ROOT/f'Complaint_Service_Hub_Program_Update_0003u36_{ts}.zip'
    include=['hub_app.py','launcher.py','updater.py','main.py','app_version.json','manifest.json','docs/UPDATE_MODEL.txt']
    manifest={'package_type':'program_update','format_version':1,'created_at':datetime.datetime.now().isoformat(timespec='seconds'),'source_build':'0003u36','files':include}
else:
    out=ROOT/f'Complaint_Service_Hub_Master_Update_{ts}.zip'
    include=[]
    for folder in ['masters','templates','profiles']:
        include += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    manifest={'package_type':'master_update','format_version':1,'created_at':datetime.datetime.now().isoformat(timespec='seconds'),'source_build':'0003u36','files':include}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('complaint_service_hub/update_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    for rel in include:
        p=ROOT/rel
        if p.exists(): z.write(p, 'complaint_service_hub/'+rel)
print(out)
