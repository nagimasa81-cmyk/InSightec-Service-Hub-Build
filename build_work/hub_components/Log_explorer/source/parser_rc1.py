from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

FILE_METADATA: dict[str, dict[str, Any]] = {}
CSA_CGA_FILE_METADATA = FILE_METADATA
MONTHS = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
FILENAME_PATTERNS = [
    re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[_-]+(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[_-]+(?P<d>\d{1,2})[_-]+(?P<h>\d{1,2})[_-]+(?P<mi>\d{1,2})(?:[_-]+(?P<s>\d{1,2}))?[_-]+(?P<y>20\d{2})", re.I),
    re.compile(r"(?P<y>20\d{2})[_-](?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[_-](?P<d>\d{1,2})(?:[_-](?P<h>\d{1,2})[_-](?P<mi>\d{1,2})(?:[_-](?P<s>\d{1,2}))?)?", re.I),
]
TIME_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})(?:[:.](?P<f>\d{1,6}))?$")
WS_ROW_RE = re.compile(r"^\s*(?P<time>\d{1,2}:\d{2}:\d{2}(?:[:.]\d{1,6})?)\s+(?P<type>[A-Za-z]{3})\s+(?P<state>\S+)\s+(?P<num>\d+)\s*(?P<message>.*)$")
CSA_ROW_RE = re.compile(r"^\s*(?P<time>\d{1,2}:\d{2}:\d{2}(?:[:.]\d{1,6})?)\s+(?P<type>[A-Za-z]{3})\s+(?P<num>\d+)\s*(?P<message>.*)$")
PROCESS_RE = re.compile(r"Process\s*<(?P<process>[^>]+)>\s*Version<(?P<version>[^>]+)>", re.I)
RELEASE_RE = re.compile(r"(?P<release>.*?Release.*?)\[v\s*(?P<release_date>[^\]]+)\]", re.I)
BRACKET_RE = re.compile(r"^\[(?P<status>[^\]]+)\]\s*(?P<rest>.*)$")
NUMERIC_ANGLE_RE = re.compile(r"^\s*<\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*>\s*(?P<unit>.*)$")
VIMEASURE_HEADER_RE = re.compile(r"^;\s*Data:\s*(?P<columns>.+)$")
VIMEASURE_ROW_RE = re.compile(r"^(?P<time>\d{1,2}:\d{2}:\d{2}:\d{3})\s+(?P<values>.+)$")


def filename_datetime(path: Path) -> Optional[datetime]:
    for pat in FILENAME_PATTERNS:
        m=pat.search(path.name)
        if not m: continue
        g=m.groupdict()
        try:
            return datetime(int(g['y']), MONTHS[g['mon'].lower()], int(g['d']), int(g.get('h') or 0), int(g.get('mi') or 0), int(g.get('s') or 0))
        except Exception: pass
    return None


def parse_time(value:str, day:date, prev:Optional[datetime]) -> datetime:
    m=TIME_RE.match(value)
    if not m: raise ValueError(value)
    f=(m.group('f') or '')
    us=int((f+'000000')[:6]) if f else 0
    ts=datetime(day.year,day.month,day.day,int(m.group('h')),int(m.group('m')),int(m.group('s')),us)
    if prev and ts<prev and (prev-ts)>timedelta(hours=12): ts+=timedelta(days=1)
    return ts


def numeric_payload(text:str) -> tuple[str, Optional[float], str]:
    m=NUMERIC_ANGLE_RE.match(text.strip())
    if not m: return text.strip(), None, ''
    raw=m.group('value'); unit=m.group('unit').strip()
    return (raw + ((' '+unit) if unit else ''), float(raw), unit)


def split_status(message:str, indented:bool, parent_status:str='') -> tuple[str,str,str,Optional[float],str]:
    text=message.strip()
    status=''; sub=''; remainder=text
    b=BRACKET_RE.match(text)
    if b:
        status=b.group('status').strip(); remainder=b.group('rest').strip()
        if '=' in remainder:
            left,right=remainder.split('=',1); sub=left.strip(); remainder=right.strip()
    elif indented:
        status=parent_status
        # Prefer :: then :; if neither, split trailing <...> so parameter name becomes SubStatus.
        if '::' in text:
            sub,remainder=text.split('::',1)
        elif ':' in text and not re.match(r'^[A-Za-z]:\\',text):
            sub,remainder=text.split(':',1)
        else:
            ma=re.match(r'^(?P<name>.+?)\s+(?P<value><[^>]+>.*)$', text)
            if ma: sub=ma.group('name').strip(); remainder=ma.group('value').strip()
    else:
        # C++ Class::Method: remainder
        if '::' in text:
            left,rest=text.split('::',1); status=left.strip()
            if ':' in rest:
                sub,remainder=rest.split(':',1)
            else: sub=rest.strip(); remainder=''
        elif ':' in text and not re.match(r'^[A-Za-z]:\\',text):
            parts=text.split(':',2)
            status=parts[0].strip(); remainder=':'.join(parts[1:]).strip()
            if len(parts)==3:
                sub=parts[1].strip(); remainder=parts[2].strip()
    clean,num,unit=numeric_payload(remainder)
    return status.strip(),sub.strip(),clean,num,unit


def parse_ws(path:Path, lines:list[str]) -> list[dict[str,Any]]:
    base=filename_datetime(path)
    if base is None: raise ValueError(f'WS filename date not found: {path.name}')
    out=[]; prev=None
    for n,raw0 in enumerate(lines,1):
        raw=raw0.rstrip('\r\n'); m=WS_ROW_RE.match(raw)
        if not m: continue
        ts=parse_time(m.group('time'),base.date(),prev); prev=ts
        structured={'Type':m.group('type'),'State':m.group('state'),'Num':m.group('num')}
        out.append({'timestamp':ts,'source_type':'WS','filename':path.name,'line_no':n,'level':m.group('type'),'category':m.group('state'),'message':m.group('message').strip(),'raw':json.dumps(structured,ensure_ascii=False),'parser':'RC1_WS_STRUCTURED_V2'})
    return out


def header_metadata(path:Path, lines:list[str], source:str)->dict[str,Any]:
    md={'source_type':source,'file':path.name,'header_lines_skipped':min(4,len(lines))}
    for line in lines[:4]:
        m=PROCESS_RE.search(line)
        if m: md.update(process=m.group('process').strip(),version=m.group('version').strip())
        m=RELEASE_RE.search(line)
        if m: md.update(release=m.group('release').strip(),release_date=m.group('release_date').strip())
    FILE_METADATA[str(path.resolve())]=md
    return md


def parse_csa_cga(path:Path, source:str, lines:list[str])->list[dict[str,Any]]:
    base=filename_datetime(path)
    if base is None: raise ValueError(f'{source} filename date not found: {path.name}')
    md=header_metadata(path,lines,source); out=[]; prev=None; ptype=''; pnum=''; parent_status=''
    for n,raw0 in enumerate(lines[4:],5):
        raw=raw0.rstrip('\r\n')
        if not raw.strip(): continue
        m=CSA_ROW_RE.match(raw)
        if m:
            ts=parse_time(m.group('time'),base.date(),prev); prev=ts; ptype=m.group('type'); pnum=m.group('num')
            msg=m.group('message'); indented=len(msg)-len(msg.lstrip(' \t'))>0; text=msg.lstrip(' \t')
        else:
            if prev is None: continue
            ts=prev; text=raw.lstrip(' \t'); indented=True
        status,sub,msg,numval,unit=split_status(text,indented,parent_status)
        if status: parent_status=status
        data={'Type':ptype,'Num':pnum,'Status':status,'SubStatus':sub,'NumericValue':numval,'Unit':unit}
        if not out: data['_file_metadata']=md
        out.append({'timestamp':ts,'source_type':source,'filename':path.name,'line_no':n,'level':ptype,'category':status or sub,'message':msg,'raw':json.dumps(data,ensure_ascii=False),'parser':f'RC1_{source}_STRUCTURED_V2'})
    return out


def parse_watersystem(path:Path, lines:list[str])->list[dict[str,Any]]:
    base=filename_datetime(path); day=base.date() if base else None; prev=None; fields=[]; out=[]
    default=['MainState','CoolingState','Error','ChillerTemp','PrimaryFlowMeter','AbsolutePressure','DynamicPressure','XdTemperature','VacuumLevel','DOLevel','WaterVolume','SecondaryFlowMeter','HsCombitac','ChillerStatus','ChillerLowLevelInd','PressureSetPoint']
    for n,raw0 in enumerate(lines,1):
        raw=raw0.strip()
        if not raw: continue
        parts=raw.split(); t=parts[0]
        if TIME_RE.match(t) and day:
            ts=parse_time(t,day,prev); prev=ts; vals=parts[1:]
        else: continue
        if 'MainState' in vals and 'Error' in vals: fields=vals; continue
        use=fields or default; data={}
        for key,val in zip(use,vals):
            if key=='CoolingState': continue
            if key in {'MainState','Error'}: data[key]=val
            else:
                try:data[key]=float(val)
                except:data[key]=val
        err=str(data.get('Error',''))
        if err.upper() in {'NO_ERROR','NOERROR','NONE','OK','0'}: data['Error']=''; err=''
        out.append({'timestamp':ts,'source_type':'WATERSYSTEM','filename':path.name,'line_no':n,'level':'Err' if err else '','category':str(data.get('MainState','')),'message':'','raw':json.dumps(data,ensure_ascii=False),'parser':'RC1_WATERSYSTEM_V2'})
    return out


def parse_vimeasure(path:Path, lines:list[str])->list[dict[str,Any]]:
    base=filename_datetime(path)
    if base is None: raise ValueError(f'VIMeasure filename date not found: {path.name}')
    cols=[]; prev=None; out=[]
    for n,raw0 in enumerate(lines,1):
        raw=raw0.strip()
        mh=VIMEASURE_HEADER_RE.match(raw)
        if mh: cols=mh.group('columns').split(); continue
        mr=VIMEASURE_ROW_RE.match(raw)
        if not mr or not cols: continue
        ts=parse_time(mr.group('time'),base.date(),prev); prev=ts
        vals=mr.group('values').split(); data={}
        for key,val in zip(cols,vals):
            try:data[key]=float(val)
            except:data[key]=val
        out.append({'timestamp':ts,'source_type':'VIMEASURE','filename':path.name,'line_no':n,'level':'','category':'VIMeasure','message':'','raw':json.dumps(data,ensure_ascii=False),'parser':'RC1_VIMEASURE_BUILTIN_V1'})
    return out


def parse_rc1_file(path:Path, source_type:str, lines:list[str], enable_builtin_vimeasure:bool=True)->Optional[list[dict[str,Any]]]:
    source=str(source_type).upper()
    if source=='WS': return parse_ws(path,lines)
    if source in {'CSA','CGA'}: return parse_csa_cga(path,source,lines)
    if source=='WATERSYSTEM': return parse_watersystem(path,lines)
    if source=='VIMEASURE' and enable_builtin_vimeasure: return parse_vimeasure(path,lines)
    return None
