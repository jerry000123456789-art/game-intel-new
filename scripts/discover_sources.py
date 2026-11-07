#!/usr/bin/env python3
"""Produce a review queue from actual RSS items; never manufacture structured facts."""
import json, pathlib, datetime, re, urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[1]
src=json.loads((ROOT/'data/latest.json').read_text(encoding='utf-8'))
items=src.get('items',[])
labels={'兌換碼':'codes','遊戲攻略':'guides','活動行事曆':'events'}
patterns={'codes':re.compile(r'兌換碼|禮包碼|redeem|\bcodes?\b',re.I),'guides':re.compile(r'攻略|培養|配隊|guide|build|walkthrough',re.I),'events':re.compile(r'活動|聯動|周年|週年|儲值|卡池|event|collab|top.up',re.I)}
leads={k:[] for k in patterns}; seen=set()
for item in items:
    if not isinstance(item,dict):continue
    title=str(item.get('title','')).strip(); url=str(item.get('url','')).strip()
    u=urllib.parse.urlparse(url)
    if not title or u.scheme!='https' or not u.hostname:continue
    for category,kind in labels.items():
        if item.get('category')!=category or not patterns[kind].search(title):continue
        key=(kind,url)
        if key in seen:continue
        seen.add(key)
        leads[kind].append({'title':title,'source_url':url,'publisher':item.get('publisher',''),'published_at':item.get('published_at',''),'first_seen_at':item.get('first_seen_at',''),'status':'source_lead_only'})
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
out={'updated_at':now,'note':'These are source leads, not verified codes, full guides, or confirmed events.','items':leads}
path=ROOT/'data/source_leads.json';path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('source_leads '+', '.join(f'{k}={len(v)}' for k,v in leads.items()))
