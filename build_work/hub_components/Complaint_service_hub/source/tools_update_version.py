from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BUILD='0003u39c'
VERSION='0.5.0-alpha.0003u39c'
for name in ('version.json','app_version.json','manifest.json'):
    path=ROOT/name
    if not path.exists(): continue
    data=json.loads(path.read_text(encoding='utf-8'))
    if 'version' in data: data['version']=VERSION
    if 'build' in data: data['build']=BUILD
    if 'commit' in data: data['commit']=BUILD
    data['build_timestamp_utc']=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    data['source_revision']=os.environ.get('GITHUB_SHA','local')[:12]
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Updated version metadata: {VERSION} / {BUILD}')
