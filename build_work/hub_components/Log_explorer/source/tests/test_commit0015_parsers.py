from pathlib import Path
import json, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from parser_rc1 import parse_ws, parse_csa_cga, parse_vimeasure
ROOT=Path(__file__).resolve().parents[1]
ws=Path('/mnt/data/2026_Apr_11_07_52_18.Log')
csa=Path('/mnt/data/Csa_Brain_650_Thu_Jun_18_20_35_48_2026.txt')
cga=Path('/mnt/data/CGA_Brain_650_Thu_Jun_18_20_35_43_2026.txt')
vi=Path('/mnt/data/VIMeasure_Wed_Jan_22_22_06_02_2025(1).txt')
for p in [ws,csa,cga,vi]:
    assert p.exists(),p
wr=parse_ws(ws,ws.read_text(encoding='latin-1').splitlines()); assert wr and json.loads(wr[0]['raw']).keys()>={'Type','State','Num'}
cr=parse_csa_cga(csa,'CSA',csa.read_text(encoding='latin-1').splitlines()); assert cr and cr[0]['line_no']>=5
cg=parse_csa_cga(cga,'CGA',cga.read_text(encoding='latin-1').splitlines()); assert cg
vr=parse_vimeasure(vi,vi.read_text(encoding='latin-1').splitlines()); assert len(vr)>1000 and '4vI' in json.loads(vr[0]['raw'])
# Numeric <> extraction must exist in CSA sample.
nums=[json.loads(r['raw']).get('NumericValue') for r in cr]
assert any(v is not None for v in nums)
print(f'PASS WS={len(wr)} CSA={len(cr)} CGA={len(cg)} VIMEASURE={len(vr)}')
