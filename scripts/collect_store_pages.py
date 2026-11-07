#!/usr/bin/env python3
"""Read public store listings and append grounded catalog entries.

A listing's FIRST-SEEN date is NOT a release date. Treat blocked/dynamic pages as
source errors and retain previous records. Never manufacture game names.
"""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
OUTPUT = ROOT/'data/game_catalog.json'
HEALTH = ROOT/'data/store_health.json'
SOURCES = [
    ('Google Play','台灣','https://play.google.com/store/games?hl=zh_TW&gl=TW'),
    ('Google Play','國際','https://play.google.com/store/games?hl=zh_TW&gl=US'),
    ('App Store','台灣','https://apps.apple.com/tw/iphone/games'),
    ('Huawei AppGallery','國際','https://appgallery.huawei.com/tab/automore%7Cdoublecolumncardwithstar%7C903189%7CA01000'),
]
MAX_HTML = 5_000_000

class StoreLinks(HTMLParser):
    def __init__(self, platform):
        super().__init__(convert_charrefs=True)
        self.platform=platform
        self.current=None
        self.links=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a':
            href=urllib.parse.unquote(a.get('href',''))
            is_play=self.platform=='Google Play' and '/store/apps/details' in href and 'id=' in href
            is_apple=self.platform=='App Store' and bool(re.search(r'/app/[^/?#]+/id\d+',href))
            self.current={'href':href, 'parts':[a.get('aria-label',''),a.get('title','')], 'depth':1} if (is_play or is_apple) else self.current
            if self.current and self.current['href']!=href:self.current['depth']+=1
        elif self.current and tag=='img':
            self.current['parts'].append(a.get('alt',''))
    def handle_data(self, data):
        if self.current:self.current['parts'].append(data)
    def handle_endtag(self, tag):
        if tag=='a' and self.current:
            c=self.current
            c['depth']-=1
            if c['depth']<=0:
                self.links.append(c)
                self.current=None


def normalized_link(platform, href, region):
    base='https://play.google.com' if platform=='Google Play' else 'https://apps.apple.com'
    u=urllib.parse.urljoin(base,href)
    p=urllib.parse.urlparse(u)
    if platform=='Google Play':
        if p.hostname!='play.google.com':return ''
        appid=urllib.parse.parse_qs(p.query).get('id',[''])[0]
        if not re.fullmatch(r'[A-Za-z][\w.]{3,180}',appid):return ''
        return 'https://play.google.com/store/apps/details?'+urllib.parse.urlencode({'id':appid,'hl':'zh_TW','gl':'TW' if region=='台灣' else 'US'})
    if p.hostname!='apps.apple.com':return ''
    m=re.search(r'/id(\d+)',p.path)
    return ('https://apps.apple.com/tw/app/id'+m.group(1)) if m else ''


def title_for(platform, candidates):
    for raw in candidates:
        t=' '.join(raw.split())
        t=re.sub(r'\s*(?:[0-5](?:\.\d)?\s*star|\d+(?:\.\d)?\s*顆星).*$', '', t,flags=re.I).strip()
        if 2 <= len(t) <= 95 and not re.fullmatch(r'\d+[,.]?\d*',t) and not t.startswith('https://'):
            # The app name is metadata from the store link, not a guessed release date.
            return t
    return ''


def parse_store(html,platform,region):
    parser=StoreLinks(platform)
    parser.feed(html)
    found={}
    for x in parser.links:
        link=normalized_link(platform,x['href'],region)
        title=title_for(platform,x['parts'])
        if not link or not title:continue
        key=link
        if key not in found:
            found[key]={
                'id':hashlib.sha256((platform+'|'+region+'|'+link).encode()).hexdigest()[:22],
                'name':title,'status':'商店收錄','region':region,
                'platforms':[platform],'release_date':'','developer':'','cover_url':'',
                'store_links':[{'name':platform,'url':link,'region':region}],
                'payment_methods':[],'source_url':link,
                'verified_store_listing':True,
                'first_seen_at':NOW,
            }
    return list(found.values())


def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; GameIntelPublicListing/1.0)','Accept':'text/html,application/xhtml+xml'})
    with urllib.request.urlopen(req,timeout=22) as resp:
        if resp.status!=200:raise RuntimeError('HTTP '+str(resp.status))
        data=resp.read(MAX_HTML+1)
        if len(data)>MAX_HTML:raise RuntimeError('response exceeds 5 MB')
        return data.decode('utf-8','replace')


def run():
    existing=json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else {'items':[]}
    old=existing.get('items',[])
    key=lambda x:(x.get('name','').strip().casefold(),tuple(x.get('platforms',[])),x.get('region',''))
    merged={key(x):x for x in old if x.get('name')}
    previous=json.loads(HEALTH.read_text(encoding='utf-8')) if HEALTH.exists() else {'sources':{}}
    health=previous.get('sources',{})
    fresh=0
    for platform,region,url in SOURCES:
        name=platform+' '+region
        s=health.get(name,{})
        try:
            if platform=='Huawei AppGallery':
                # Evaluate public HTML rather than pretending JS-rendered listings were scraped.
                html=fetch(url)
                raise RuntimeError('官網為動態渲染，無可核對的遊戲清單擷取規則（'+str(len(html))+' bytes）')
            data=parse_store(fetch(url),platform,region)
            if not data:raise RuntimeError('頁面未解析出可核對的遊戲連結')
            for x in data:
                k=key(x)
                if k in merged:
                    prior=merged[k]
                    x['first_seen_at']=prior.get('first_seen_at') or prior.get('discovered_at') or NOW
                    # Preserve confirmed details over the generic store-listing snapshot.
                    for field in ('release_date','developer','cover_url'):
                        x[field]=prior.get(field) or x[field]
                    if prior.get('status') not in ('商店收錄','已上市',''):
                        x['status']=prior['status']
                else:fresh+=1
                merged[k]=x
            s={'state':'success','last_checked_at':NOW,'last_success_at':NOW,'items_this_run':len(data),'source_url':url}
        except Exception as exc:
            s={'state':'error','last_checked_at':NOW,'last_success_at':s.get('last_success_at',''),'items_this_run':0,'error':str(exc)[:220],'source_url':url}
        health[name]=s
        print(f'{name}: {s["state"]}, items={s["items_this_run"]}'+ (' ERROR '+s.get('error','') if s['state']=='error' else ''))
    records=list(merged.values())
    records.sort(key=lambda x:(x.get('first_seen_at',''),x.get('release_date','')),reverse=True)
    # Only rewrite catalog when new/changed records actually found; source state separately tracks failures.
    if records!=old:
        existing['items']=records
        existing['updated_at']=NOW
        existing['note']='商店清單收錄日期與遊戲正式上市日期不同；未提供的上市日期保留空白。'
        OUTPUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    HEALTH.write_text(json.dumps({'updated_at':NOW,'sources':health},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Store catalog: total='+str(len(records))+' newly_added='+str(fresh))
    return fresh

if __name__=='__main__':run()
