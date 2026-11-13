#!/usr/bin/env python3
"""Focused radar UI and data snapshot validations."""
from html.parser import HTMLParser
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
class IDs(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,tag,attrs):self.ids.extend(v for k,v in attrs if k=='id')
text=(ROOT/'index.html').read_text(encoding='utf8')
p=IDs();p.feed(text)
required={'game-search','game-list','market-filter','detail-dialog','pagination','result-title','health-errors'}
errors=[]
for x in required-set(p.ids):errors.append('Missing UI element: '+x)
for x in set(p.ids):
 if p.ids.count(x)>1:errors.append('Duplicate id: '+x)
for name in ('radar_catalog','radar_summary','radar_health'):
 try:
  j=json.loads((ROOT/'data'/(name+'.json')).read_text(encoding='utf8'))
  if name=='radar_catalog' and not isinstance(j.get('games'),list):errors.append('radar_catalog games must be array')
 except Exception as exc:errors.append(name+': '+str(exc))
if not all(x in text for x in ['新上市','即將上市','預約／預先註冊','Google Play','App Store','詳細資訊']):errors.append('Missing visible Chinese labels')
for bad in ['兌換碼','攻略／創作者','宣傳工作區','多平台文案工作台','首次發布日期待確認','已確認可下載']:
 if bad in text:errors.append('Obsolete visible feature or text: '+bad)
if errors:
 print('\n'.join(errors),file=sys.stderr);sys.exit(1)
print('Focused mobile radar static checks passed.')
