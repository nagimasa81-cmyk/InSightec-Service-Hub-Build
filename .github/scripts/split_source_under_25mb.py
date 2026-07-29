from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

LIMIT = 25 * 1024 * 1024
DEFAULT_PART = 20 * 1024 * 1024

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('--part-size-mb', type=int, default=20)
    ns=ap.parse_args()
    src=ns.source.resolve()
    part_size=ns.part_size_mb*1024*1024
    if not src.is_file(): raise SystemExit(f'File not found: {src}')
    if part_size >= LIMIT: raise SystemExit('Part size must be below 25 MB')
    parts=[]
    with src.open('rb') as f:
        index=1
        while True:
            data=f.read(part_size)
            if not data: break
            out=src.with_name(src.name+f'.part{index:03d}')
            out.write_bytes(data)
            parts.append({'name':out.name,'size':out.stat().st_size,'sha256':digest(out)})
            index+=1
    manifest=src.with_name(src.name+'.parts.json')
    manifest.write_text(json.dumps({'source':src.name,'source_size':src.stat().st_size,'source_sha256':digest(src),'parts':parts},indent=2),encoding='utf-8')
    print(manifest)
    return 0
if __name__=='__main__': raise SystemExit(main())
