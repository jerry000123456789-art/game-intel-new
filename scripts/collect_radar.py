#!/usr/bin/env python3
"""Free-source mobile-game radar discovery: broad Play search + Apple new-game RSS.

No paid APIs. Every source has its own success/error log; a search result is
a lead until an official product URL can be parsed/verified. A store update
date is NEVER an initial release date. Source limits do NOT imply full coverage.
"""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, quote, urlparse, parse_qs, unquote
from urllib.request import Request, urlopen
import sys
from html.parser import HTMLParser
import html as html_lib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_store_pages as stores
from enrich_mobile_store import metadata_from_html
CONFIG=ROOT/"config/radar_sources.json"
DISC=ROOT/"data/radar_discoveries.json"
HEALTH=ROOT/"data/radar_health.json"
NOW=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
COUNTRY_NAMES={"TW":"台灣","US":"美國","JP":"日本","KR":"韓國","HK":"香港","SG":"新加坡"}
UA={"User-Agent":"Mozilla/5.0 (compatible; GameIntelRadar/2.0; public product metadata)","Accept":"text/html,application/json,application/xml"}
MAX_BYTES=3_500_000

def fetch(url,limit=MAX_BYTES):
    req=Request(url,headers=UA)
    with urlopen(req,timeout=16) as r:
        if r.status!=200:raise RuntimeError("HTTP "+str(r.status))
        data=r.read(limit+1)
        if len(data)>limit:raise RuntimeError("body too large")
        return data.decode("utf-8","replace")

def appid(url,store):
    u=urlparse(str(url or ""))
    if store=="Google Play":
        if u.hostname!="play.google.com":return ""
        return parse_qs(u.query).get("id",[""])[0]
    if u.hostname!="apps.apple.com":return ""
    m=re.search(r"/id(\d+)",u.path)
    return m.group(1) if m else ""

def official_url(store,ident,country):
    if store=="Google Play":
        return "https://play.google.com/store/apps/details?"+urlencode({"id":ident,"hl":"zh_TW","gl":country})
    return f"https://apps.apple.com/{country.lower()}/app/id{ident}"

def date_only(s):
    try:return dt.date.fromisoformat(str(s or "")[:10]).isoformat()
    except ValueError:return ""

def identity(row):
    store=row.get("store","")
    return (store,row.get("app_id",""),row.get("country","")) if store in ("Google Play","App Store") else ()

def normalize(row):
    s=dict(row)
    store=s.get("store") or (s.get("platforms") or [""])[0]
    if store not in ("Google Play","App Store"):return None
    country=str(s.get("country") or ("TW" if s.get("region")=="台灣" else "US")).upper()
    if country not in COUNTRY_NAMES:return None
    ident=s.get("app_id") or appid(s.get("source_url") or (s.get("store_links") or [{}])[0].get("url"),store)
    if not ident:return None
    name=str(s.get("name") or "").strip()
    if not name:return None
    return {"store":store,"app_id":ident,"country":country,"name":name,
      "developer":str(s.get("developer") or ""),"cover_url":s.get("cover_url") or "",
      "source_url":official_url(store,ident,country),
      "release_date":date_only(s.get("release_date")),
      "date_scope":s.get("date_scope") or s.get("date_label") or "",
      "preorder":bool(s.get("preorder") or s.get("preorder_confirmed") or s.get("status") in ("預先註冊","預約")),
      "installable":bool(s.get("installable") or s.get("officially_installed")),
      "first_seen_at":s.get("first_seen_at") or s.get("first_seen_in_country_at") or NOW,
      "last_checked_at":s.get("last_checked_at") or s.get("checked_at") or "",
      "source_kind":s.get("source_kind") or "商店公開資料",
      "detail_note":s.get("detail_note") or "",
      "verified_store_listing":bool(s.get("verified_store_listing",True))}

def merge(table,raw):
    row=normalize(raw)
    if not row:return
    key=identity(row)
    previous=table.get(key)
    if not previous:
        table[key]=row;return
    combined=dict(previous)
    # Keep oldest detection history, not first time a new scraping run happens.
    times=[x for x in (previous.get("first_seen_at"),row.get("first_seen_at")) if x]
    combined["first_seen_at"]=min(times) if times else NOW
    if row.get("name") and (row.get("source_kind") in ("Play 官方商品頁","Apple Lookup","Apple 新上架 RSS")
            or not previous.get("name")):combined["name"]=row["name"]
    for field in ("developer","cover_url","last_checked_at"):
        if row.get(field):combined[field]=row[field]
    if row.get("release_date"):
        if not combined.get("release_date") or row.get("date_scope")=="官方發行日期":
            combined["release_date"]=row["release_date"]
            combined["date_scope"]=row.get("date_scope","")
    # The current official check overrides historic pre-registration state.
    if row.get("source_kind") in ("Play 官方商品頁","Apple Lookup"):
        # A page without readable availability controls is inconclusive:
        # never wipe a known preregistration state just because its check
        # returned no recognizable button.
        if row["preorder"]:
            combined["preorder"]=True
            combined["installable"]=False
        elif row["installable"]:
            combined["preorder"]=False
            combined["installable"]=True
        combined["last_checked_at"]=NOW
        combined["source_kind"]=row["source_kind"]
    else:
        combined["preorder"]=bool(previous.get("preorder") or row.get("preorder"))
        combined["installable"]=bool(previous.get("installable") or row.get("installable"))
    combined["verified_store_listing"]=previous.get("verified_store_listing") or row.get("verified_store_listing")
    table[key]=combined

def apple_feed(data,country,feedkind):
    feed=data.get("feed",{})
    records=feed.get("entry") or []
    if isinstance(records,dict):records=[records]
    out=[]
    for e in records:
        try:
            title=e["im:name"]["label"].strip()
            link=e.get("link",{});link=link[0] if isinstance(link,list) else link
            url=link.get("attributes",{}).get("href","") if isinstance(link,dict) else ""
            ident=appid(url,"App Store")
            if not ident or not title:continue
            image=e.get("im:image") or []
            art=image[-1].get("label","") if isinstance(image,list) and image else ""
            developer=e.get("im:artist",{}).get("label","")
            rd=e.get("im:releaseDate",{}).get("label","")
            out.append({"store":"App Store","app_id":ident,"country":country,
                "name":title,"developer":developer,"cover_url":art,"source_url":official_url("App Store",ident,country),
                "release_date":date_only(rd),"date_scope":"Apple 商品發行日期，非國家首發保證",
                "source_kind":"Apple 新上架 RSS" if feedkind.startswith("new") else "Apple 遊戲排行榜",
                "first_seen_at":NOW,"verified_store_listing":True})
        except (KeyError,AttributeError,IndexError,TypeError):continue
    return out

def apple_lookup(ident,country):
    url="https://itunes.apple.com/lookup?"+urlencode({"id":ident,"country":country.lower(),"entity":"software"})
    j=json.loads(fetch(url,600000))
    for a in j.get("results",[]):
        if str(a.get("trackId"))!=ident or a.get("kind")!="software":continue
        isgame=a.get("primaryGenreName")=="Games" or "6014" in [str(i) for i in a.get("genreIds",[])]
        if not isgame:return None
        d=date_only(a.get("releaseDate"))
        return {"store":"App Store","app_id":ident,"country":country,
            "name":a.get("trackName","").strip(),"developer":a.get("artistName",""),
            "cover_url":a.get("artworkUrl512") or a.get("artworkUrl100",""),
            "source_url":official_url("App Store",ident,country),
            "release_date":d,"date_scope":"Apple 商品發行日期，非各國首發日期",
            "preorder":bool(a.get("isPreOrder") or a.get("isPreorder")),
            "installable":bool(d and d<=dt.datetime.now(dt.timezone.utc).date().isoformat()
                               and not (a.get("isPreOrder") or a.get("isPreorder"))),
            "source_kind":"Apple Lookup","last_checked_at":NOW,"first_seen_at":NOW,
            "verified_store_listing":True}
    return None

class PlayTitleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta=[];self.title=[];self.heading=[];self.capture=""
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta" and (a.get("property","").lower() in ("og:title","twitter:title") or
                            a.get("name","").lower() in ("og:title","twitter:title","application-name")):
            if a.get("content"):self.meta.append(a["content"].strip())
        if tag in ("title","h1"):self.capture=tag
    def handle_data(self,data):
        if self.capture=="title":self.title.append(data)
        elif self.capture=="h1":self.heading.append(data)
    def handle_endtag(self,tag):
        if tag==self.capture:self.capture=""
def google_details(ident,country):
    url=official_url("Google Play",ident,country)
    body=fetch(url)
    data=metadata_from_html(body)
    parser=PlayTitleParser()
    parser.feed(body[:1500000])
    title=""
    for candidate in [*parser.meta,*parser.heading,*parser.title]:
        value=html_lib.unescape(str(candidate)).strip()
        # Only accept an actual game title, never the Play search/consent page.
        value=re.split(r"\s+[-–]\s+(?:Google Play|Apps on Google Play|Google Play 應用程式)",value,flags=re.I)[0].strip()
        if 2<=len(value)<=140 and not re.search(r"Google Play|Sign in|登入 Google|Redirecting",value,re.I):
            title=value;break
    if not title:
        # Inspect actual accessible HTML for error diagnostics; do not
        # invent a title based solely on the requested package ID.
        return None
    return {"store":"Google Play","app_id":ident,"country":country,"name":title[:110],
        "developer":"","cover_url":data.get("cover_url",""),
        "source_url":url,"release_date":date_only(data.get("store_release_date")),
        "date_scope":"官方發行日期" if data.get("store_release_date") else "",
        "preorder":bool(data.get("preorder_confirmed")),"installable":bool(data.get("officially_installed")),
        "source_kind":"Play 官方商品頁","last_checked_at":NOW,"first_seen_at":NOW,
        "verified_store_listing":True}

def google_search_query(query,country):
    # Official Google Play search, not only its editorial home. It does not
    # promise a complete catalog and it may return recommendations/non-games.
    url="https://play.google.com/store/search?"+urlencode({
      "q":query,"c":"apps","hl":"zh_TW","gl":country})
    rows=stores.parse_store(fetch(url),"Google Play","台灣" if country=="TW" else "國際",country)
    for x in rows:
        x["country"]=country
        x["source_kind"]="Play 搜尋結果（待商品核實）"
    return rows

def google_web_leads(query):
    # Google public HTML may be blocked: this must fail visibly, never imply
    # successful Google-wide crawling. Only extract actual official product IDs.
    url="https://www.google.com/search?"+urlencode({"q":'site:play.google.com/store/apps/details '+query,"num":30,"hl":"zh-TW"})
    body=fetch(url,1000000)
    ids=set(re.findall(r"(?:id=|id%3D)([A-Za-z][\w.]{3,150})",unquote(body),re.I))
    return ids

def run(fetch_only=False):
    config=json.loads(CONFIG.read_text(encoding="utf8"))
    old=json.loads(DISC.read_text(encoding="utf8")) if DISC.exists() else {"items":[]}
    table={}
    for x in old.get("items",[]):merge(table,x)
    health={"updated_at":NOW,"sources":[],"errors":[],"new_records":0,"attempts":0,
       "scope":"公開商店與搜尋資料；不保證各市場全部新上架遊戲",
       "note":"Google 搜尋／App Store RSS 屬部分清單，未取得日期不以更新日替代首發。"}
    def log(kind,url,records=None,error=""):
        entry={"kind":kind,"url":url,"checked_at":NOW,"state":"error" if error else "success",
          "count":len(records) if records is not None else 0}
        if error:entry["error"]=str(error)[:200];health["errors"].append(entry)
        health["sources"].append(entry);health["attempts"]+=1
    def fetch_apple_feeds():
        for country in config["apple_feed_countries"]:
            for kind in config["apple_feed_kinds"]:
                url=f"https://itunes.apple.com/{country.lower()}/rss/{kind}/limit=100/genre=6014/json"
                try:
                    batch=apple_feed(json.loads(fetch(url)),country,kind)
                    if not batch:raise RuntimeError("empty/unparseable feed")
                    for x in batch:merge(table,x)
                    log("Apple "+kind,url,batch)
                except Exception as e:log("Apple "+kind,url,error=e)
    fetch_apple_feeds()
    queries=config["google_queries"]
    google_markets=config.get("google_markets",["TW","US"])
    if google_markets!=["TW","US"]:
        raise ValueError("Google Play must use TW and the owner-selected US international storefront only")
    allocation=config.get("google_search_allocation",{"TW":8,"US":4})
    hour=int(dt.datetime.now(dt.timezone.utc).timestamp()//(3*3600))
    wanted=[(x["id"],c) for x in config["direct_google_ids"] for c in google_markets]
    # Four sample games are always rechecked. Then cycle new discovery terms.
    discovered=set(wanted)
    for url in config.get("google_categories",[]):
        country=parse_qs(urlparse(url).query).get("gl",["TW"])[0].upper()
        if country not in google_markets:
            # Never collect other-country Google Play categories into the main radar.
            continue
        try:
            rows=stores.parse_store(fetch(url),"Google Play",
                 "台灣" if country=="TW" else "國際",country)
            if not rows:raise RuntimeError("empty/unparseable category")
            for x in rows:
                x["country"]=country
                is_prereg="promotion_3000000d51_pre_registration_games" in url
                x["source_kind"]="Play 預先註冊合輯" if is_prereg else "Play 搜尋分類"
                if is_prereg:x["preorder"]=True
                merge(table,x)
                ident=appid(x.get("source_url"),"Google Play")
                if ident:discovered.add((ident,country))
            log("Google Play 分類",url,rows)
        except Exception as e:log("Google Play 分類",url,error=e)
    qcount=min(int(config.get("google_searches_per_run",12)),len(queries))
    for i in range(qcount):
        q=queries[(hour*qcount+i)%len(queries)]
        # TW dominates the coverage; US is the owner's designated "國際" store.
        # Distribute checks across the entire interval instead of all TW then US.
        tw_quota=max(0,min(qcount,int(allocation.get("TW",8))*qcount//12))
        country="TW" if (i*tw_quota)//qcount != ((i-1)*tw_quota)//qcount else "US"
        # Correct the first term and handle extreme quotas deterministically.
        if i==0:country="TW" if tw_quota else "US"
        url="https://play.google.com/store/search?"+urlencode({"q":q,"c":"apps","hl":"zh_TW","gl":country})
        try:
            rows=google_search_query(q,country)
            if not rows:raise RuntimeError("no official game links found")
            for x in rows:
                merge(table,x)
                ident=appid(x.get("source_url"),"Google Play")
                if ident:discovered.add((ident,country))
            log("Google Play 搜尋",url,rows)
        except Exception as e:log("Google Play 搜尋",url,error=e)
    # Small Google-wide discovery probe, not Google Search API and not a
    # fabricated claim that all Google results were crawled.
    for q in [queries[(hour+3)%len(queries)],queries[(hour+9)%len(queries)]]:
        try:
            ids=google_web_leads(q)
            for ident in ids:discovered.add((ident,"TW"))
            log("Google 公開搜尋", "https://www.google.com/search?q="+quote(q),list(ids))
        except Exception as e:log("Google 公開搜尋","https://www.google.com/search?q="+quote(q),error=e)
    # Official per-product verification prioritized by direct seeds + unseen
    # IDs, with a bounded rotation over older games for continuous rechecks.
    seed_set=set(wanted)
    new=[x for x in discovered if ("Google Play",x[0],x[1]) not in table]
    other=sorted(discovered-set(new)-seed_set,
                 key=lambda x:table.get(("Google Play",x[0],x[1]),{}).get("last_checked_at",""))
    checks=list(dict.fromkeys(wanted+new[:65]+other[:30]))[:100]
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        futures={pool.submit(google_details,ident,country):(ident,country) for ident,country in checks}
        for result in concurrent.futures.as_completed(futures):
            ident,country=futures[result]
            try:
                item=result.result()
                if item:
                    merge(table,item);log("Google Play 商品核實",item["source_url"],[item])
                else:log("Google Play 商品核實",official_url("Google Play",ident,country),error="商品頁無可驗證名稱")
            except Exception as e:
                log("Google Play 商品核實",official_url("Google Play",ident,country),error=e)
    direct=[(x["id"],c) for x in config["direct_apple_ids"] for c in ("TW","US","JP","KR")]
    ids=[(x[1],x[2]) for x in table if x[0]=="App Store"]
    missing=[x for x in ids if x not in direct and not table[("App Store",x[0],x[1])].get("last_checked_at")]
    # Bounded Apple Lookup, rotate across all discovered iOS entries.
    selected=list(dict.fromkeys(direct+missing[:85]+ids[(hour*90)%max(1,len(ids)):(hour*90)%max(1,len(ids))+35]))[:125]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(apple_lookup,ident,country):(ident,country) for ident,country in selected}
        for result in concurrent.futures.as_completed(futures):
            ident,country=futures[result];url=official_url("App Store",ident,country)
            try:
                item=result.result()
                if item:merge(table,item);log("Apple Lookup",url,[item])
                else:log("Apple Lookup",url,error="Apple API no game result; country availability inconclusive")
            except Exception as e:log("Apple Lookup",url,error=e)
    rows=sorted(table.values(),key=lambda x:(x.get("first_seen_at",""),x["store"],x["app_id"],x["country"]),reverse=True)
    health["new_records"]=len(rows)-len(old.get("items",[]))
    health["collected_variants"]=len(rows)
    DISC.write_text(json.dumps({"updated_at":NOW,"items":rows,
       "note":"同一 app ID 各市場分別記錄；商店查核成功仍不代表其首次上市日已查明。"},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    HEALTH.write_text(json.dumps(health,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"collected_variants":len(rows),"new_records":health["new_records"],
       "checks":health["attempts"],"failed":len(health["errors"])},ensure_ascii=False))

if __name__=="__main__":run()
