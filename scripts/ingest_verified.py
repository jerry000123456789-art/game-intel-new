#!/usr/bin/env python3
"""Import explicitly sourced game records from configured trusted JSON feeds.
Never infer codes, dates, guides, or payment methods from headline text.
"""
import json, pathlib, urllib.request, urllib.parse, datetime, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
CFG=ROOT/'config/verified_sources.json'
config=json.loads(CFG.read_text(encoding='utf8'))
LIMIT=2_000_000

def stamp(s):
    try: return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    except (ValueError,AttributeError): return None

def valid(kind,r):
    if not isinstance(r,dict):return False
    required={'codes':['game','code','discovered_at','source_url'], 'guides':['game','title','category','content','updated_at','source_url'], 'events':['game','title','start_at','end_at','region','category','source_url']}[kind]
    if not all(isinstance(r.get(k),str) and r[k].strip() for k in required):return False
    u=urllib.parse.urlparse(r['source_url'])
    if u.scheme!='https' or not u.hostname:return False
    if kind=='codes':
        return bool(stamp(r['discovered_at'])) and len(r['code'])<=128 and len(r['code'])>=3 and not any(c.isspace() for c in r['code']) and r.get('expired') in (None,True,False)
    if kind=='guides':return bool(stamp(r['updated_at'])) and len(r['content'])>=80
    a,b=stamp(r['start_at']),stamp(r['end_at'])
    return bool(a and b and a.tzinfo and b.tzinfo and b>a)

def key(kind,r):
    return tuple(r[k] for k in {'codes':['game','code'],'guides':['game','title'],'events':['game','title','start_at']}[kind])

failures=[]
for feed in config.get('feeds',[]):
    kind=feed.get('kind'); url=feed.get('url',''); hosts=feed.get('allowed_hosts',[])
    parsed=urllib.parse.urlparse(url)
    if kind not in ('codes','guides','events') or parsed.scheme!='https' or not hosts or parsed.hostname not in hosts:
        failures.append('Invalid feed configuration');continue
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'GameIntelFeedImporter/1.0','Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=18) as response:
            if response.status!=200:raise ValueError('HTTP '+str(response.status))
            raw=response.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError('Feed exceeds 2 MB')
        payload=json.loads(raw)
        records=payload.get('items') if isinstance(payload,dict) else payload
        if not isinstance(records,list):raise ValueError('items must be array')
        accepted=[]
        for r in records:
            if not valid(kind,r):continue
            sourcehost=urllib.parse.urlparse(r['source_url']).hostname
            if sourcehost not in hosts:continue
            accepted.append(r)
        path=ROOT/'data'/f'{kind}.json'
        current=json.loads(path.read_text(encoding='utf8'))
        old=current.get('items',[])
        # Preserve manually curated records and previously imported records. Never delete on empty or transient errors.
        merged={key(kind,r):r for r in old if valid(kind,r)}
        for r in accepted:merged[key(kind,r)]=r
        if accepted:
            current['items']=list(merged.values());current['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            path.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(f'{kind}: source={parsed.hostname}, received={len(records)}, accepted={len(accepted)}, total={len(merged)}')
    except Exception as e:
        failures.append(f'{kind} {parsed.hostname}: {str(e)[:160]}')
for e in failures:print('WARN:',e,file=sys.stderr)
print('Verified feed ingestion complete; failures='+str(len(failures)))
