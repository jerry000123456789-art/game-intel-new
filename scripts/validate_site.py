#!/usr/bin/env python3
"""Lightweight checks for deployable static UI and structured data."""
from html.parser import HTMLParser
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
class IDs(HTMLParser):
    def __init__(self):super().__init__();self.ids=[]
    def handle_starttag(self,tag,attrs):
        self.ids.extend(v for k,v in attrs if k=='id')
html=(ROOT/'index.html').read_text(encoding='utf-8')
p=IDs();p.feed(html)
required={'news','codes','guides','calendar','gameGrid','gamePlatform','gameSort','codeList','guideLeads','eventLeads','calendarView'}
errors=[]
for x in required-set(p.ids):errors.append('Missing UI element: '+x)
for x in set(p.ids):
    if p.ids.count(x)>1:errors.append('Duplicate id: '+x)
for file in ['latest','classified','launch_leads','game_catalog','source_leads','codes','guides','events']:
    try:json.loads((ROOT/'data'/f'{file}.json').read_text(encoding='utf-8'))
    except Exception as exc:errors.append(f'{file}.json: {exc}')
if errors:
    print('\n'.join(errors),file=sys.stderr);sys.exit(1)
print('Static site checks passed; all 8 JSON data files parse and required UI sections exist.')
