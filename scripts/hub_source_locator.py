import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

module_dir = Path("Module") / "InSightec_Service_hub"
target = Path("_hub_source")
required = {
    "InSightecServiceHub.py",
    "Build_Hub_EXE.py",
    "Build_Integrated_Tools.py",
    "Fast_Preflight_All_Tools.py",
}

def marker_prefix(names):
    prefixes = None
    for marker in required:
        current = set()
        for name in names:
            normalized = name.replace("\\", "/")
            if normalized == marker:
                current.add("")
            elif normalized.endswith("/" + marker):
                current.add(normalized[:-len(marker)])
        prefixes = current if prefixes is None else prefixes & current
    if not prefixes:
        return None
    return sorted(prefixes, key=lambda p: (len(p), p))[0]

def valid_hub_zip(path):
    try:
        with zipfile.ZipFile(path, "r") as z:
            bad = z.testzip()
            if bad:
                return None
            prefix = marker_prefix(set(z.namelist()))
            return prefix
    except Exception:
        return None

def extract_valid(path):
    prefix = valid_hub_zip(path)
    if prefix is None:
        return False
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(path, "r") as z:
        if prefix == "":
            z.extractall(target)
        else:
            plen = len(prefix)
            for info in z.infolist():
                name = info.filename.replace("\\", "/")
                if not name.startswith(prefix):
                    continue
                relative = name[plen:]
                if not relative:
                    continue
                dest = target / relative
                if info.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as src_f, dest.open("wb") as dst_f:
                        shutil.copyfileobj(src_f, dst_f)
    return True

# 1. Normal ZIP candidates. Newest valid Hub SOURCE wins.
valid = []
for path in module_dir.glob("*.zip"):
    prefix = valid_hub_zip(path)
    if prefix is not None:
        valid.append(path)
        print(f"[HUB SOURCE] valid ZIP: {path.name}")
    elif "SOURCE" in path.name.upper():
        print(f"[HUB SOURCE] reject non-Hub ZIP: {path.name}")

if valid:
    valid.sort(key=lambda p: (p.stat().st_mtime_ns, p.name.lower()), reverse=True)
    chosen = valid[0]
    if not extract_valid(chosen):
        raise SystemExit(f"Selected Hub ZIP failed extraction validation: {chosen}")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as f:
        f.write(f"source_zip_name={chosen.name}\n")
    print(f"[PASS] Auto-selected Hub SOURCE by content: {chosen.name}")
    raise SystemExit(0)

# Helpers for split sources.
def reconstruct(parts, output_zip):
    parts = sorted(parts, key=lambda x: x[0])
    numbers = [n for n, _ in parts]
    if numbers != list(range(1, len(parts) + 1)):
        return False
    with output_zip.open("wb") as out:
        for _, part in parts:
            with part.open("rb") as inp:
                shutil.copyfileobj(inp, out)
    return output_zip.is_file()

# 2. Loose .zip.partNNN families.
groups = {}
for part in module_dir.glob("*.zip.part*"):
    name = part.name
    marker = name.lower().rfind(".zip.part")
    if marker < 0:
        continue
    source_name = name[:marker + 4]
    suffix = name[marker + len(".zip.part"):]
    if suffix.isdigit():
        groups.setdefault(source_name, []).append((int(suffix), part))

split_valid = []
for source_name, parts in groups.items():
    output_zip = module_dir / source_name
    created = reconstruct(parts, output_zip)
    if created and valid_hub_zip(output_zip) is not None:
        split_valid.append(output_zip)
        print(f"[HUB SOURCE] valid loose split: {source_name}")
    elif created:
        output_zip.unlink(missing_ok=True)

if split_valid:
    split_valid.sort(key=lambda p: (p.stat().st_mtime_ns, p.name.lower()), reverse=True)
    chosen = split_valid[0]
    if not extract_valid(chosen):
        raise SystemExit(f"Selected split Hub ZIP failed extraction validation: {chosen}")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as f:
        f.write(f"source_zip_name={chosen.name}\n")
    print(f"[PASS] Auto-selected loose-split Hub SOURCE by content: {chosen.name}")
    raise SystemExit(0)

# 3. Packaged split ZIP: outer ZIP contains partNNN files (and optionally manifest).
packaged_valid = []
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    for package in module_dir.glob("*.zip"):
        try:
            with zipfile.ZipFile(package, "r") as outer:
                names = [n.replace("\\", "/") for n in outer.namelist()]
                part_names = [n for n in names if ".zip.part" in n.lower()]
                if not part_names:
                    continue
                pkg_dir = td / package.stem
                pkg_dir.mkdir(parents=True, exist_ok=True)
                outer.extractall(pkg_dir)
        except Exception:
            continue

        pkg_groups = {}
        for part in pkg_dir.rglob("*.zip.part*"):
            name = part.name
            marker = name.lower().rfind(".zip.part")
            if marker < 0:
                continue
            source_name = name[:marker + 4]
            suffix = name[marker + len(".zip.part"):]
            if suffix.isdigit():
                pkg_groups.setdefault(source_name, []).append((int(suffix), part))

        for source_name, parts in pkg_groups.items():
            rebuilt = td / ("rebuilt_" + source_name)
            if reconstruct(parts, rebuilt) and valid_hub_zip(rebuilt) is not None:
                materialized = module_dir / source_name
                shutil.copy2(rebuilt, materialized)
                packaged_valid.append((package.stat().st_mtime_ns, package.name, materialized))
                print(f"[HUB SOURCE] valid packaged split: {package.name} -> {source_name}")

if packaged_valid:
    packaged_valid.sort(key=lambda x: (x[0], x[1].lower()), reverse=True)
    chosen = packaged_valid[0][2]
    if not extract_valid(chosen):
        raise SystemExit(f"Selected packaged-split Hub ZIP failed extraction validation: {chosen}")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as f:
        f.write(f"source_zip_name={chosen.name}\n")
    print(f"[PASS] Auto-selected packaged-split Hub SOURCE by content: {chosen.name}")
    raise SystemExit(0)

visible = sorted(p.name for p in module_dir.iterdir() if p.is_file())
raise SystemExit(
    "No valid Service Hub SOURCE found. A valid Hub SOURCE must contain "
    "InSightecServiceHub.py, Build_Hub_EXE.py, Build_Integrated_Tools.py, "
    f"and Fast_Preflight_All_Tools.py. Files in folder: {visible}"
)
