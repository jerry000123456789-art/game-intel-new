#!/usr/bin/env python3
"""Poll public news for games the owner chose. No inferred event dates."""
import datetime as dt,email.utils,hashlib,json,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; NOW=dt.datetime.now(dt.timezone.utc)
CONF=ROOT/'config/tracked_games.json'; OUTPUT=ROOT/'data/tracked_events.json'; LIST=ROOT/'data/tracked_games.json'
DATE=re.compile(r'(20\d{2})[-/.年](1[0-2]|0?[1-9])[-/.月](3[01]|[12]\d|0?[1-9])(?:日)?')
BOUND=re.compile(r'活動期間|活動時間|舉辦期間|event period|event dates?',re.I)
EVENT=re.compile(r'活動|聯動|慶典|限時|賽季|週年|event|collab|festival',re.I)
def bounded_dates(title,description):
    text=re.sub(r'<[^>]+>',' ',title+' '+description)
    match=BOUND.search(text)
    if not match:return ('','')
    found=list(DATE.finditer(text[match.start():match.start()+145]))
    if len(found)<2:return ('','')
    try:
        dates=[dt.date(int(m[1]),int(m[2]),int(m[3])) for m in found[:2]]
        if dates[0]>dates[1] or (dates[1]-dates[0]).days>150:return ('','')
    except ValueError:return ('','')
    return dates[0].isoformat(),dates[1].isoformat()
def parse_feed(raw,game,now=NOW):
    root=ET.fromstring(raw); out=[];cutoff=now-dt.timedelta(days=32)
    for item in root.findall('./channel/item'):
        title=(item.findtext('title') or '').strip()
        url=(item.findtext('link') or '').strip()
        if not title or game.casefold() not in title.casefold() or not EVENT.search(title) or not url.startswith('https://'):continue
        try:
            when=email.utils.parsedate_to_datetime(item.findtext('pubDate') or '')
            if when.tzinfo is None:when=when.replace(tzinfo=dt.timezone.utc)
            if when<cutoff:continue
        except (ValueError,TypeError):continue
        a,b=bounded_dates(title,item.findtext('description') or '')
        source=item.find('source')
        out.append({'id':hashlib.sha256((game+'|'+url).encode()).hexdigest()[:24],
            'game':game,'title':title[:200],'source_url':url,'published_at':when.isoformat(),
            'publisher':source.text if source is not None and source.text else '',
            'start_date':a,'end_date':b,'date_status':'公告明示日期，請核對來源' if a else '日期待公布'})
    return out
def poll(name):
    query='"'+name+'" (遊戲活動 OR 限時活動 OR 聯動 OR 慶典) when:30d'
    params=urllib.parse.urlencode({'q':query,'hl':'zh-TW','gl':'TW','ceid':'TW:zh-Hant'})
    req=urllib.request.Request('https://news.google.com/rss/search?'+params,headers={'User-Agent':'GameIntelWatch/1.0'})
    with urllib.request.urlopen(req,timeout=18) as response:return parse_feed(response.read(1500000),name)
def main():
    cfg=json.loads(CONF.read_text(encoding='utf8'))
    games=[g for g in cfg.get('games',[]) if isinstance(g,dict) and 2<=len(g.get('name',''))<=80][:35]
    previous=json.loads(OUTPUT.read_text(encoding='utf8')) if OUTPUT.exists() else {'items':[]}
    known={x['id']:x for x in previous.get('items',[]) if x.get('id')}
    errs=[];done=0
    for item in games:
        try:
            for entry in poll(item['name']):
                entry['first_seen_at']=known.get(entry['id'],{}).get('first_seen_at') or NOW.isoformat()
                known[entry['id']]=entry
            done+=1
        except Exception as e:errs.append({'game':item['name'],'error':str(e)[:150]})
    cutoff=(NOW-dt.timedelta(days=120)).isoformat()
    active={g['name'].casefold() for g in games}
    items=sorted((x for x in known.values() if x.get('game','').casefold() in active and x.get('published_at','')>=cutoff),key=lambda x:x.get('published_at',''),reverse=True)[:600]
    LIST.write_text(json.dumps({'updated_at':NOW.isoformat(),'games':games},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    OUTPUT.write_text(json.dumps({'updated_at':NOW.isoformat(),'items':items,'successful_checks':done,'errors':errs,'note':'刊登時間不等於活動時間；未定日期公告不進日曆'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Tracking: games',len(games),'checked',done,'announcements',len(items),'errors',len(errs))
if __name__=='__main__':main()
