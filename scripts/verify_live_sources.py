#!/usr/bin/env python3
"""Verify that at least one network source actually returned data this run.
No fake 'success' when mocks or stale local data are all that's available.
"""
import json,sys,datetime as dt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data'
now=dt.datetime.now(dt.timezone.utc)
def read(name):
    p=ROOT/f'{name}.json'
    return json.loads(p.read_text(encoding='utf8')) if p.exists() else {}
def recent(s):
    try:return abs((now-dt.datetime.fromisoformat(s.replace('Z','+00:00'))).total_seconds())<3600
    except Exception:return False
channels=read('channel_history')
stores=read('store_health')
latest=read('latest')
extract=read('extraction_status')
results={
 'YouTube/巴哈 RSS':bool(channels.get('fetched',0)>0 and recent(channels.get('updated_at',''))),
 '商店公開頁面':any(x.get('state')=='success' and recent(x.get('last_checked_at','')) for x in stores.get('sources',{}).values()),
 '新聞 RSS':bool(latest.get('status') in ('ok','partial') and recent(latest.get('updated_at','')) and latest.get('fetched',0)>0),
 '內容來源':bool(extract.get('sources_succeeded',0)>0 and recent(extract.get('updated_at',''))),
}
report={'checked_at':now.isoformat(),'live_sources':results,'at_least_one_live_source':any(results.values()),
        'note':'單次來源回應成功並不代表 Cloudflare 已完成部署，須再核對正式網站。'}
(ROOT/'runtime_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for name,ok in results.items():print(('PASS' if ok else 'FAIL')+': '+name)
if not report['at_least_one_live_source']:
    print('FAIL: every live source unavailable; no source was verifiably fetched in this run',file=sys.stderr)
    sys.exit(1)
print('PASS: live network collection verified (>=1 source); each source status remains visible')
