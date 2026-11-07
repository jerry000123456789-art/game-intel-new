#!/usr/bin/env python3
"""Fetch publicly available article pages and identify explicit codes / event dates.

- Code candidates are labeled untested; source_url is mandatory.
- No activity has dates guessed from a headline or post time.
- No third-party full article is reproduced; link back to the publisher.
- Failed source fetch never erases previous records.
"""
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CONF=json.loads((ROOT/'config/content_sources.json').read_text(encoding='utf8'))
NOW=dt.datetime.now(dt.timezone.utc)
NOW_ISO=NOW.isoformat(timespec='seconds')
MAX_DOC=1_500_000
MAX_ARTICLES=50
CODE_REGEX=re.compile(r'(?:兌換碼|序號|禮包碼|福利碼|redeem(?:ption)?\s*codes?|promo\s*codes?)\s*(?:[:：\-－]|為|是|：\s*|\s+)\s*[「\[\(]?([A-Za-z0-9]{6,25})', re.I)
# Four digit years required. No date-of-publication fallback.
DATES=re.compile(r'(20\d\d)[-/年.](0?[1-9]|1[0-2])[-/月.](3[01]|[12]\d|0?[1-9])(?!\d)(?:日)?(?:\s*(?:上午|下午)?\s*([01]?\d|2[0-3]):([0-5]\d))?')
EVENT_WORDS=re.compile(r'活動|聯動|慶典|節日|賽季|event|collaboration|festival|期間限定|週年|周年',re.I)
STOP={'REDEEM','REDEMPTION','GENSHIN','HONKAI','GAMING','REWARDS','REWARD','EXPIRED','UNKNOWN','VOUCHER','ALLCODES','PROMOCODE','GIFT CODE'}

class ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in ('script','style','noscript','svg'):self.skip+=1
        if t in ('p','td','tr','li','h1','h2','h3','br','code','div'):self.parts.append(' \n ')
    def handle_endtag(self,t):
        if t in ('script','style','noscript','svg') and self.skip:self.skip-=1
        if t in ('p','td','tr','li','br','code'):self.parts.append(' \n ')
    def handle_data(self,s):
        if not self.skip:self.parts.append(s)

def content(html):
    p=ReadableHTML();p.feed(html);return ' '.join(''.join(p.parts).split())

def eligible_code(code):
    if not 6<=len(code)<=25:return False
    if code.upper() in STOP:return False
    if re.fullmatch(r'20\d{6,}',code):return False
    if not re.search('[A-Za-z]',code):return False
    return True

def extract_codes(game, body, source_url, published_at=''):
    if not game:return []
    candidates=[];found=set()
    for m in CODE_REGEX.finditer(body):
        c=m.group(1)
        if not eligible_code(c) or c.casefold() in found:continue
        found.add(c.casefold())
        candidates.append({'game':game,'code':c,'discovered_at':NOW_ISO,
            'source_url':source_url,'source_published_at':published_at,
            'verification_note':'自動從公開來源整理；未在遊戲內實測',
            'verification_status':'未實測','expired':False})
    return candidates

def extract_event(game,title,body,source_url):
    if not game or not EVENT_WORDS.search(title+' '+body[:350]):return []
    # Explicit date range on a single source page; article dates are not event dates.
    candidates=[]
    # Prefer paragraphs mentioning event times, not arbitrary unrelated dates.
    for m in re.finditer(r'(?:活動時間|活動期間|舉辦期間|期間|event\s*duration|event\s*period)\s*[:：]?\s*([^\n]{0,160})',body,re.I):
        text=m.group(1)
        dates=list(DATES.finditer(text))
        if len(dates)<2:continue
        try:
            start=dt.datetime(int(dates[0][1]),int(dates[0][2]),int(dates[0][3]),int(dates[0][4] or '0'),int(dates[0][5] or '0'),tzinfo=dt.timezone(dt.timedelta(hours=8)))
            end=dt.datetime(int(dates[1][1]),int(dates[1][2]),int(dates[1][3]),int(dates[1][4] or '23'),int(dates[1][5] or '59'),tzinfo=dt.timezone(dt.timedelta(hours=8)))
        except ValueError:continue
        if end<=start or (end-start).days>180:continue
        candidates.append({'game':game,'title':title[:180], 'start_at':start.isoformat(), 'end_at':end.isoformat(),
            'region':'未註明','category':'活動公告','source_url':source_url,
            'extraction_status':'自動擷取，日期以來源為準',
            'topup_notes':'自動擷取公開公告中的活動期間，請點原始來源核對時區與資格'})
        break
    return candidates

def match_game(text):
    normalized=text.lower()
    games=set(CONF['known_games'])
    catalog=ROOT/'data/game_catalog.json'
    if catalog.exists():
        try:games.update(x.get('name','').strip() for x in json.loads(catalog.read_text(encoding='utf8')).get('items',[]))
        except (ValueError,OSError):pass
    for game in sorted((x for x in games if len(x)>=2),key=len,reverse=True):
        if game.lower() in normalized:return game.replace('崩壞 星穹鐵道','崩壞：星穹鐵道')
    # Quoted game names from reporting; only used as attribution for a clear code/date.
    m=re.search(r'《([^》]{2,45})》',text)
    return m.group(1).strip() if m else ''

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; GameIntelArticleCollector/1.0)'})
    with urllib.request.urlopen(req,timeout=14) as resp:
        if resp.status!=200:raise RuntimeError('HTTP '+str(resp.status))
        data=resp.read(MAX_DOC+1)
        if len(data)>MAX_DOC:raise RuntimeError('too large')
        if 'html' not in resp.headers.get('Content-Type','text/html').lower():raise RuntimeError('not HTML')
        return data.decode('utf-8','replace')

def recent_rows():
    out=[];seen=set();cutoff=NOW-dt.timedelta(days=CONF.get('lookback_days',10))
    for name in ('channel_history','latest'):
        path=ROOT/'data'/f'{name}.json'
        if not path.exists():continue
        for item in json.loads(path.read_text(encoding='utf8')).get('items',[]):
            url=item.get('url','');title=item.get('title','')
            pub=item.get('published_at','')
            try:
                when=dt.datetime.fromisoformat(pub.replace('Z','+00:00'))
                if when.tzinfo is None:when=when.replace(tzinfo=dt.timezone.utc)
                if when<cutoff:continue
            except (ValueError,AttributeError):continue
            u=urllib.parse.urlparse(url)
            if u.scheme!='https' or u.hostname not in CONF['news_domains'] or url in seen:continue
            if not re.search(r'兌換碼|禮包碼|福利碼|redeem|攻略|活動|event|聯動|期間',title,re.I):continue
            seen.add(url);out.append((item,title,url))
    return sorted(out,key=lambda x:x[0].get('published_at',''),reverse=True)[:MAX_ARTICLES]

def update_records(name, rows, keys):
    p=ROOT/'data'/f'{name}.json';dat=json.loads(p.read_text(encoding='utf8'))
    old=dat['items'];merged={tuple(str(x.get(k,'')).casefold() for k in keys):x for x in old}
    count=0
    for row in rows:
        k=tuple(str(row.get(k,'')).casefold() for k in keys)
        if k not in merged:merged[k]=row;count+=1
    if count:
        dat['items']=list(merged.values());dat['updated_at']=NOW_ISO
        p.write_text(json.dumps(dat,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return count,len(merged)

def run():
    work=[({'published_at':''},s['game'],s['url']) for s in CONF['code_pages']]
    work += [(item,match_game(title),link) for item,title,link in recent_rows()]
    codes=[];events=[];errors=[];ok=0
    for item,game,url in work:
        if not game:continue
        try:
            body=content(fetch(url))
            title=item.get('title','') or game+' 公開兌換碼'
            codes+=extract_codes(game,body,url,item.get('published_at',''))
            if item.get('title'):events+=extract_event(game,title,body,url)
            ok+=1
        except Exception as e:errors.append({'url':url,'error':str(e)[:160]})
    added_codes,total_codes=update_records('codes',codes,('game','code'))
    added_events,total_events=update_records('events',events,('game','title','start_at'))
    # Source failures visible in website status; do not treat them as successes.
    status={'updated_at':NOW_ISO,'sources_attempted':len(work),'sources_succeeded':ok,'errors':errors[:50],
            'codes':{'new':added_codes,'total':total_codes},'events':{'new':added_events,'total':total_events}}
    (ROOT/'data/extraction_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Content extraction:',json.dumps({k:v for k,v in status.items() if k!='errors'},ensure_ascii=False),'errors='+str(len(errors)))
    return status

if __name__=='__main__':run()
