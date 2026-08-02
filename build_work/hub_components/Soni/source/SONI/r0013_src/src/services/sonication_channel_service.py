from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class SonicationChannel:
    channel: int | None
    source: Path | None = None
    raw_line: str | None = None

class SonicationChannelService:
    _PATTERNS=(
        re.compile(r"(?:hydrophone|spectrum|acoustic)\s*(?:channel|ch)?\s*[:=]\s*(?:ch)?\s*([0-7])",re.I),
        re.compile(r"(?:selected|active)\s*(?:channel|ch)\s*[:=]\s*(?:ch)?\s*([0-7])",re.I),
        re.compile(r"\bCH\s*([0-7])\b",re.I),
    )
    def read(self, folder: Path) -> SonicationChannel:
        files=sorted((p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.act','.ini','.cfg','.conf','.txt','.xml'}),key=lambda p:(0 if p.suffix.lower()=='.act' else 1,len(p.parts),p.name.lower()))
        for path in files:
            try: text=path.read_text(encoding='utf-8',errors='ignore')
            except OSError: continue
            for line in text.splitlines():
                for pattern in self._PATTERNS:
                    match=pattern.search(line)
                    if match: return SonicationChannel(int(match.group(1)),path,line.strip())
        return SonicationChannel(None)
