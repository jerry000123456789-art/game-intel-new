#!/usr/bin/env python3
"""Collect YouTube/Bahamut public RSS history, retain earlier entries and dedupe.
RSS is a rolling window; historical backfill beyond its available entries requires another source.
"""
import datetime as dt, email.utils, hashlib, json, pathlib, urllib.request, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
output=ROOT/'data/channel_history.json'
prior=json.loads(output.read_text(encoding='utf-8')) if output.exists() else {'items':[]}
old={x['id']:x for x in prior.get('items',[])}
now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
feeds=[('YouTube',f'https://www.youtube.com/feeds/videos.xml?channel_id={ch}') for ch in config.get('youtube_channels',[])]
feeds += [('巴哈姆特',u) for u in config.get('bahamut_feeds',[])]
errors=[]; fetched=0
for origin,feed in feeds:
 try:
  req=urllib.request.Request(feed,headers={'User-Agent':'Mozilla/5.0 GameIntel/1.0'})
  with urllib.request.urlopen(req,timeout=18) as resp: raw=resp.read(2_000_000)
  root=ET.fromstring(raw)
  entries=root.findall('{http://www.w3.org/2005/Atom}entry') if root.tag.endswith('feed') else root.findall('./channel/item')
  for e in entries:
   atom=root.tag.endswith('feed')
   def txt(name):return (e.findtext('{http://www.w3.org/2005/Atom}'+name) if atom else e.findtext(name)) or ''
   title=txt('title').strip()
   lk=e.find('{http://www.w3.org/2005/Atom}link') if atom else None
   link=(lk.get('href','') if lk is not None else txt('link')).strip()
   if not title or not link.startswith('https://'):continue
   published=(txt('published') or txt('updated')) if atom else txt('pubDate')
   if not atom:
    try:published=email.utils.parsedate_to_datetime(published).isoformat()
    except Exception:published=''
   publisher=txt('author') if not atom else (e.findtext('{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name') or '')
   ident=hashlib.sha256((origin+'|'+link).encode()).hexdigest()[:24]
   old[ident]={'id':ident,'category':'影片情報' if origin=='YouTube' else '巴哈姆特情報','origin':origin,'title':title[:240], 'url':link,'publisher':publisher,'published_at':published,'first_seen_at':old.get(ident,{}).get('first_seen_at',now)}
   fetched+=1
 except Exception as exc:errors.append({'source':feed,'error':str(exc)[:160]})
rows=sorted(old.values(),key=lambda x:x.get('published_at') or x.get('first_seen_at',''),reverse=True)[:2000]
output.write_text(json.dumps({'updated_at':now,'status':'ok' if not errors else ('partial' if fetched else 'error'),'fetched':fetched,'errors':errors,'items':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'channel_history: total={len(rows)} fetched={fetched} errors={len(errors)}')
if errors and not fetched:print('WARN: No live YouTube/Bahamut feed succeeded; retained history')
