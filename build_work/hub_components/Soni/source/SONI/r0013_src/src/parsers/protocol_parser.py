from pathlib import Path
from .ado_rowset import parse_ado_rowset

def parse(path: str | Path):
    return parse_ado_rowset(path)
