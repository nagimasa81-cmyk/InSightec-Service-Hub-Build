from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def discover():
    registry=json.loads((ROOT/'config/module_registry.json').read_text(encoding='utf-8'))
    found=[]
    for folder in sorted((ROOT/'Module').iterdir(),key=lambda p:p.name.lower()):
        manifest_path=folder/'module.json'
        if not folder.is_dir() or not manifest_path.is_file():
            continue
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        mid=str(manifest.get('id') or folder.name)
        if mid!=folder.name:
            raise SystemExit(f'module.json id mismatch: {folder.name} != {mid}')
        zips=sorted(p.name for p in folder.glob('*.zip') if 'SOURCE' in p.name.upper())
        found.append({'id':mid,'display_name':manifest.get('display_name',mid),'source_zips':zips,
                      'supports_reuse':bool(manifest.get('supports_reuse',True)),
                      'supports_hub':bool(manifest.get('supports_hub',False))})
    return found
if __name__=='__main__':
    print(json.dumps({'modules':discover()},ensure_ascii=False,indent=2))
