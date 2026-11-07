#!/usr/bin/env python3
"""Produce a machine-readable, honest audit of content and source coverage."""
import json, pathlib, datetime, sys
root=pathlib.Path(__file__).resolve().parents[1]
now=datetime.datetime.now(datetime.timezone.utc)
config=json.loads((root/'config/verified_sources.json').read_text(encoding='utf-8'))
report={'checked_at':now.isoformat(),'verified_feeds':len(config.get('feeds',[])),'sections':{},'warnings':[]}
for name in ('latest','game_catalog','codes','guides','events'):
    data=json.loads((root/'data'/f'{name}.json').read_text(encoding='utf-8'))
    rows=data.get('items',[])
    report['sections'][name]={'count':len(rows)}
    if not rows: report['warnings'].append(f'{name}: no content')
if not report['verified_feeds']:
    report['warnings'].append('No configured verified automatic feeds for codes/guides/events')
(root/'data'/'coverage_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
