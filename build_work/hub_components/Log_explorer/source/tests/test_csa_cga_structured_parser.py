from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from parser_rc1 import parse_rc1_file
ROOT=Path(__file__).resolve().parent

def raw_fields(row): return json.loads(row['raw'])

def validate(kind,name):
    p=ROOT/'samples'/name
    rows=parse_rc1_file(p,kind,p.read_text(encoding='utf-8',errors='ignore').splitlines())
    assert rows and rows[0]['line_no']==5
    md=raw_fields(rows[0])['_file_metadata']
    assert md['header_lines_skipped']==4 and md['process'].upper()==kind and md['version']=='6.33.25.(00)'
    assert md['release_date'].startswith('Jun 14 2022')
    assert rows[0]['timestamp'].year==2026 and rows[0]['level'] in {'Inf','Wrn','Err'} and raw_fields(rows[0])['Num'].isdigit()
    water=next(r for r in rows if raw_fields(r).get('SubStatus')=='IsWaterSystemControl')
    assert water['category']=='WATER_SYSTEM' and water['message']=='1' and raw_fields(water)['Status']=='WATER_SYSTEM'
    server=next(r for r in rows if r['category']=='SERVER' and 'connected successfully' in r['message'])
    assert raw_fields(server)['Status']=='SERVER' and raw_fields(server)['SubStatus'] and server['message']=='was connected successfully'

def main():
    validate('CSA','Csa_Brain_650_Thu_Jun_18_20_35_48_2026.txt')
    validate('CGA','CGA_Brain_650_Thu_Jun_18_20_35_43_2026.txt')
    print('Commit0017 R1 CSA/CGA structured parser tests: PASS')
    return 0
if __name__=='__main__': raise SystemExit(main())
