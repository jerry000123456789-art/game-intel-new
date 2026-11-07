#!/usr/bin/env python3
"""Stable historical dedupe, newest record wins; never invent source data."""
import json,pathlib,datetime
root=pathlib.Path(__file__).resolve().parents[1]/'data'
keys={'codes':('game','code'),'guides':('game','title'),'events':('game','title','start_at')}
for kind,fields in keys.items():
 p=root/(kind+'.json'); data=json.loads(p.read_text(encoding='utf8')); records=data.get('items',[])
 merged={}
 for x in records:
  if not isinstance(x,dict):continue
  key=tuple(str(x.get(k,'')).strip().casefold() for k in fields)
  if not all(key):continue
  prev=merged.get(key)
  if prev is None or (x.get('updated_at') or x.get('discovered_at') or '')>(prev.get('updated_at') or prev.get('discovered_at') or ''):merged[key]=x
 if len(merged)!=len(records):
  data['items']=list(merged.values());p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(f'{kind}: {len(records)} -> {len(merged)} unique')
