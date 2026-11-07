#!/usr/bin/env python3
"""Show actual source coverage and content counts; don't equate feeds with verified claims."""
import datetime as dt,json,pathlib
r=pathlib.Path(__file__).resolve().parents[1]
def load(name):
 p=r/'data'/f'{name}.json'
 return json.loads(p.read_text(encoding='utf8')) if p.exists() else {}
conf=json.loads((r/'config/content_sources.json').read_text())
report={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'configured_content_pages':len(conf['code_pages']),
        'configured_youtube_channels':len(json.loads((r/'config/sources.json').read_text())['youtube_channels']),
        'sections':{},'source_health':{},'warnings':[]}
for name in ('latest','channel_history','game_catalog','codes','guides','events'):
 rows=load(name).get('items',[])
 report['sections'][name]={'count':len(rows)}
 if not rows:report['warnings'].append(name+' has no visible content')
for name in ('store_health','extraction_status','runtime_status'):
 report['source_health'][name]=load(name)
(r/'data/coverage_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Coverage:',{k:v['count'] for k,v in report['sections'].items()})
