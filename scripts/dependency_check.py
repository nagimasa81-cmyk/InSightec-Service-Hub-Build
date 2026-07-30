from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common.build_common import latest_source_zip, extract_zip, detect_requirements

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--module',required=True); ap.add_argument('--source-zip',default=''); a=ap.parse_args()
    source=latest_source_zip(ROOT/'Module'/a.module,a.source_zip)
    root=extract_zip(source,ROOT/'.dependency_check'/a.module/'source')
    reqs=detect_requirements(root)
    if not reqs:
        print('No requirements file; dependency dry-run skipped.')
        return
    # Prefer the shallowest primary requirements file. Included -r files are resolved by pip.
    primary=sorted(reqs,key=lambda p:(0 if p.name.lower()=='requirements.txt' else 1,len(p.parts),p.name))[0]
    cmd=[sys.executable,'-m','pip','install','--dry-run','--disable-pip-version-check','-r',str(primary)]
    print('[DEPENDENCY DRY-RUN]',subprocess.list2cmdline(cmd))
    rc=subprocess.call(cmd,cwd=primary.parent)
    if rc: raise SystemExit(rc)
    print('DEPENDENCY RESOLUTION PASSED')
if __name__=='__main__': main()
