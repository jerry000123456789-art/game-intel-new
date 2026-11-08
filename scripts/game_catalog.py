#!/usr/bin/env python3
"""Collect actual store game listings, not news headlines. No inferred payment methods."""
import datetime as dt, json, pathlib, urllib.request, urllib.parse, time, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
NOW=dt.datetime.now(dt.timezone.utc)
HEADERS={'User-Agent':'GameIntelCatalog/1.0 (public store metadata)'}
def fetch(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=18) as r: return json.load(r)
def record(name, status, region, platform, store, link, image='', date='', developer='', source=''):
    return {'id':platform.lower().replace(' ','-')+'-'+hashlib.sha256(link.encode()).hexdigest()[:16], 'name':name,'status':status,'region':region,'platforms':[platform], 'release_date':date,'developer':developer,'cover_url':image,'store_links':[{'name':store,'url':link,'region':region}], 'payment_methods':[], 'source_url':source or link,'verified_store_listing':True, 'date_label':'Apple 產品發行日期（非該國首次上架）' if platform=='App Store' else ''}
def country_for(x):
    country=str(x.get('country','')).upper()
    if country in ('TW','US','JP','KR','HK','SG'):return country
    u=urllib.parse.urlparse(x.get('source_url','') or (x.get('store_links') or [{}])[0].get('url',''))
    if u.hostname=='play.google.com':
        gl=urllib.parse.parse_qs(u.query).get('gl',[''])[0].upper()
        if gl:return gl
    if u.hostname=='apps.apple.com':
        part=u.path.split('/')[1:2]
        if part and part[0].upper() in ('TW','US','JP','KR','HK','SG'):return part[0].upper()
    return 'TW' if x.get('region')=='台灣' else 'US'

items=[];errors=[]
# Steam explicitly labels the upcoming category. Dates are left blank unless independently provided.
try:
    data=fetch('https://store.steampowered.com/api/featuredcategories/?cc=us&l=english')
    for x in data.get('coming_soon',{}).get('items',[])[:40]:
        appid=x.get('id'); name=x.get('name')
        if not appid or not name: continue
        link=f'https://store.steampowered.com/app/{int(appid)}/'
        items.append(record(name,'即將上市','國際','Steam','Steam',link,x.get('header_image') or f'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{int(appid)}/header.jpg'))
except Exception as e: errors.append('Steam: '+str(e)[:160])
# Apple Search API: exact title matches only, games category only, actual store pages.
seeds=['星布谷地','裝備仔','Petit Planet','OVERGEARED','Basketball Slam MyTEAM','Enchanted Inn: Merge & Mystery','巨獸重返','萌爪配對碰']
for term in seeds:
    try:
        q=urllib.parse.urlencode({'term':term,'entity':'software','country':'tw','limit':30})
        data=fetch('https://itunes.apple.com/search?'+q)
        for x in data.get('results',[]):
            name=x.get('trackName','').strip()
            if name.casefold()!=term.casefold() or x.get('primaryGenreName')!='Games':continue
            link=x.get('trackViewUrl','')
            if not link:continue
            rd=x.get('releaseDate','')[:10]
            try: future=dt.date.fromisoformat(rd)>NOW.date()
            except ValueError:future=False
            status='即將上市' if future else '已上市'
            items.append(record(name,status,'台灣','App Store','App Store',link,x.get('artworkUrl512') or x.get('artworkUrl100',''),rd,x.get('artistName','')))
    except Exception as e:errors.append('App Store '+term+': '+str(e)[:100])
    time.sleep(.15)
# Store listing dedupe; avoid inserting news-title candidates as games.
unique={}
existing=ROOT/'data/game_catalog.json'
if existing.exists():
    try:
        for x in json.loads(existing.read_text(encoding='utf-8')).get('items',[]):
            if x.get('name') and x.get('platforms'):
                if x.get('region')=='美國':
                    x['region']='國際'
                    for store in x.get('store_links',[]):
                        if store.get('region')=='美國':store['region']='國際'
                x['country']=country_for(x)
                unique[(x['name'].casefold(),x['platforms'][0],x.get('region',''),x['country'])]=x
    except (ValueError,KeyError,TypeError): pass
for x in items:
    x['country']=country_for(x)
    k=(x['name'].casefold(),x['platforms'][0],x['region'],x['country'])
    if k in unique:
        prev=unique[k]
        x['first_seen_at']=prev.get('first_seen_at') or NOW.isoformat()
        x['payment_methods']=prev.get('payment_methods',[])
        x['release_date']=x.get('release_date') or prev.get('release_date','')
        x['cover_url']=x.get('cover_url') or prev.get('cover_url','')
        x['developer']=x.get('developer') or prev.get('developer','')
    else:x['first_seen_at']=NOW.isoformat()
    unique[k]=x
if errors and not items:
    existing=ROOT/'data/game_catalog.json'
    if existing.exists():
        old=json.loads(existing.read_text(encoding='utf-8'))
        if old.get('items'):
            print('Store sources unavailable; preserving previous catalog')
            raise SystemExit(0)
    raise SystemExit('No store catalog sources available; not publishing an empty replacement: '+str(errors))
result={'updated_at':NOW.isoformat(),'items':list(unique.values()),'errors':errors,'note':'僅收錄實際商店條目；商店付款能力不代表遊戲實際支援，未核實的支付方式不顯示。'}
out=ROOT/'data/game_catalog.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'game_catalog={len(result["items"])} errors={len(errors)}')
