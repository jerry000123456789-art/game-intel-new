#!/usr/bin/env python3
"""Refresh official artwork for manually cross-checked release examples.

Never overwrite a documented historical launch date with latest update date.
"""
from pathlib import Path
import json,datetime as dt,urllib.request,urllib.parse,re
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data/featured_launches.json'
data=json.loads(PATH.read_text(encoding='utf8'))
updated=0
for row in data.get('items',[]):
    apple=next((x for x in row.get('platforms',[]) if x.get('platform')=='App Store'),None)
    if not apple:continue
    m=re.search(r'/id(\d+)',apple.get('store_url',''))
    if not m:continue
    try:
        url='https://itunes.apple.com/lookup?'+urllib.parse.urlencode({'id':m.group(1),'country':'tw'})
        req=urllib.request.Request(url,headers={'User-Agent':'GameIntelFeaturedRelease/1.0'})
        with urllib.request.urlopen(req,timeout=18) as r:
            apps=json.load(r).get('results',[])
        app=next((x for x in apps if str(x.get('trackId'))==m.group(1)),None)
        if not app:continue
        art=app.get('artworkUrl512') or app.get('artworkUrl100')
        if art and art.startswith('https://') and '.mzstatic.com/' in art:
            if art!=row.get('cover_url'):updated+=1
            row['cover_url']=art
        row['apple_product_date']=str(app.get('releaseDate') or '')[:10]
        row['apple_product_date_source']='https://apps.apple.com/tw/app/id'+m.group(1)
        row['official_store_visible']=True
    except Exception as e:
        print('Featured icon fetch limited:',row.get('name'),str(e)[:130])
data['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Featured verified titles',len(data.get('items',[])),'artwork updates',updated)
