"""Program updater. No tkinter / no GUI dependency.
Applies program update ZIP safely with backup. Intended to be called by Launcher before Hub starts.
"""
from __future__ import annotations
import sys, os, zipfile, shutil, json, datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
LOG = APP_DIR / 'logs' / 'updater.log'
PROTECTED = {'config/settings.json'}

def log(msg: str):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")

def backup_files(files):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bdir = APP_DIR / 'backups' / f'program_backup_{ts}'
    bdir.mkdir(parents=True, exist_ok=True)
    for rel in files:
        src = APP_DIR / rel
        if src.exists() and src.is_file():
            dst = bdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return bdir

def restore(bdir):
    for p in bdir.rglob('*'):
        if p.is_file():
            rel = p.relative_to(bdir)
            dst = APP_DIR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)

def apply_update(zip_path: Path) -> int:
    log(f'Applying update: {zip_path}')
    if not zip_path.exists():
        log('Update file not found')
        return 2
    with zipfile.ZipFile(zip_path, 'r') as z:
        names = [n for n in z.namelist() if not n.endswith('/')]
        # Support zips with root complaint_service_hub/ or direct paths
        rels = []
        for n in names:
            rel = n
            if rel.startswith('complaint_service_hub/'):
                rel = rel[len('complaint_service_hub/'):]
            if not rel or rel.startswith('../') or rel.startswith('/'):
                continue
            if rel in PROTECTED:
                continue
            rels.append((n, Path(rel)))
        bdir = backup_files([str(r) for _, r in rels])
        try:
            for original, rel in rels:
                dst = APP_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                with z.open(original) as src, open(dst, 'wb') as out:
                    shutil.copyfileobj(src, out)
            hist = APP_DIR / 'logs' / 'update_history.json'
            data=[]
            if hist.exists():
                try: data=json.load(open(hist, encoding='utf-8'))
                except Exception: data=[]
            data.append({'time': datetime.datetime.now().isoformat(timespec='seconds'), 'type':'program', 'zip':zip_path.name, 'backup':str(bdir.name), 'files':[str(r) for _, r in rels]})
            json.dump(data, open(hist,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
            try:
                zip_path.unlink()
            except Exception:
                pass
            log('Update success')
            return 0
        except Exception as e:
            log(f'Update failed: {e}; restoring {bdir}')
            restore(bdir)
            return 1

def main():
    if len(sys.argv) < 2:
        log('No update zip argument')
        return 2
    return apply_update(Path(sys.argv[1]))

if __name__ == '__main__':
    raise SystemExit(main())
