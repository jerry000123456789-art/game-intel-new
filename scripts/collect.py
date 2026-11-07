#!/usr/bin/env python3
"""Collect public RSS headlines. All items are unverified leads, NOT verified codes/events."""
import datetime as dt, email.utils, hashlib, json, pathlib, urllib.parse, urllib.request, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
outfile=ROOT/'data/latest.json'
old={x['id']:x for x in json.loads(outfile.read_text(encoding='utf-8')).get('items',[])} if outfile.exists() else {}
now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
errors=[]; new=[]
for item in config['queries']:
    q=item['query']; category=item['category']
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'zh-TW','gl':'TW','ceid':'TW:zh-Hant'})
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'GameIntelPublicRSS/1.0'})
        with urllib.request.urlopen(req,timeout=20) as resp: root=ET.fromstring(resp.read(2_000_000))
        for entry in root.findall('./channel/item')[:config.get('max_per_query',20)]:
            title=(entry.findtext('title') or '').strip(); link=(entry.findtext('link') or '').strip()
            if not title or not link: continue
            ident=hashlib.sha256((category+'|'+link).encode()).hexdigest()[:20]
            pub=entry.findtext('pubDate') or ''
            try: pub=email.utils.parsedate_to_datetime(pub).isoformat()
            except Exception: pub=''
            source=entry.find('source'); publisher=source.text if source is not None else ''
            new.append({'id':ident,'category':category,'title':title[:240],'url':link,'publisher':publisher or '', 'published_at':pub,'first_seen_at':old.get(ident,{}).get('first_seen_at',now)})
    except Exception as e: errors.append({'category':category,'error':str(e)[:200]})
combined={x['id']:x for x in old.values()}
combined.update({x['id']:x for x in new})
items=sorted(combined.values(),key=lambda x:x.get('published_at') or x.get('first_seen_at',''),reverse=True)[:300]
payload={'updated_at':now,'status':'ok' if not errors else 'partial','errors':errors,'fetched':len(new),'note':'RSS 標題線索，尚未驗證兌換碼、上市日期或活動細節。','items':items}
outfile.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'items={len(items)}, fetched={len(new)}, errors={len(errors)}')
if errors and not new: print('WARN: no live news RSS succeeded; retained existing data')
