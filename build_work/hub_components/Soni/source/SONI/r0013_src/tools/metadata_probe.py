from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core.metadata import MetadataManager

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('dataset')
    ap.add_argument('--json', dest='json_path')
    args=ap.parse_args()
    m=MetadataManager().load(args.dataset)
    print(f"Root: {m.root}")
    print(f"Sonications: {sorted(m.sonications)}")
    for i,s in sorted(m.sonications.items()):
        print(f"S{i}: summary={bool(s.summary)} spots={len(s.spots)} skull_files={len(s.skull.files)} elements={sum(s.skull.element_counts.values())}")
    print("Sources:")
    for k,v in m.sources.items(): print(f"  {k}: loaded={v.loaded} records={v.records} path={v.path or '-'} error={v.error or '-'}")
    if args.json_path: MetadataManager().export_json(m,args.json_path)
if __name__=='__main__': main()
