#!/usr/bin/env python3
"""Fail CI on malformed or unsupported manually curated game intelligence records."""
import json, pathlib, datetime, sys
from urllib.parse import urlparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
errors=[]
def issue(f,i,m): errors.append(f'{f}: item {i}: {m}')
def url(x):
    try: return urlparse(x).scheme=='https' and bool(urlparse(x).netloc)
    except Exception: return False
def stamp(x):
    try:
        datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
        return True
    except (ValueError,AttributeError): return False
for kind in ('codes','guides','events'):
    path=ROOT/'data'/f'{kind}.json'
    try: data=json.loads(path.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'{path}: invalid JSON: {e}');continue
    rows=data.get('items')
    if not isinstance(rows,list): errors.append(f'{path}: items must be array');continue
    seen=set()
    for i,x in enumerate(rows,1):
        if not isinstance(x,dict):issue(kind,i,'must be object');continue
        required={'codes':('game','code','discovered_at','source_url'), 'guides':('game','title','category','content','updated_at','source_url'), 'events':('game','title','start_at','end_at','region','category','source_url')}[kind]
        for key in required:
            if not isinstance(x.get(key),str) or not x[key].strip():issue(kind,i,f'missing {key}')
        if not url(x.get('source_url','')):issue(kind,i,'source_url must be valid https URL')
        for key in {'codes':['discovered_at'],'guides':['updated_at'],'events':['start_at','end_at']}[kind]:
            if x.get(key) and not stamp(x[key]):issue(kind,i,f'invalid ISO date {key}')
        if kind=='codes':
            if x.get('expired') not in (None,True,False):issue(kind,i,'expired must be boolean')
            identity=(x.get('game'),x.get('code'))
        elif kind=='guides':
            if len(x.get('content',''))<80:issue(kind,i,'guide content shorter than 80 characters')
            identity=(x.get('game'),x.get('title'))
        else:
            try:
                a=datetime.datetime.fromisoformat(x['start_at'].replace('Z','+00:00'))
                b=datetime.datetime.fromisoformat(x['end_at'].replace('Z','+00:00'))
                if a.tzinfo is None or b.tzinfo is None:issue(kind,i,'start/end must include timezone offset')
                elif b<=a:issue(kind,i,'end must be later than start')
            except (ValueError,KeyError,AttributeError):pass
            identity=(x.get('game'),x.get('title'),x.get('start_at'))
        if identity in seen:issue(kind,i,'duplicate')
        seen.add(identity)
    print(f'{kind}: {len(rows)} curated records validated')
if errors:
    print('\n'.join(errors),file=sys.stderr)
    sys.exit(1)
print('Validation passed')
