#!/usr/bin/env python3
"""Conservative cross-game advertising opportunity radar.

TapTap is a lead source, not proof of TW availability or authorization to sell.
No miHoYo / HoYoverse games are recommended. Never invent event dates or
claim Chinese-server offers work in Taiwan. Blocked site pages are reported.
"""
import datetime as dt
import email.utils
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config/ad_opportunity_sources.json"
OUT=ROOT/"data/ad_opportunities.json"
STATUS=ROOT/"data/ad_opportunity_status.json"
NOW=dt.datetime.now(dt.timezone.utc)
TODAY=(NOW+dt.timedelta(hours=8)).date()
DATE_RE=re.compile(r"(20\d{2})[-/.年](1[0-2]|0?[1-9])[-/.月](3[01]|[12]\d|0?[1-9])(?!\d)(?:日)?")
RANGE_MARKER=re.compile(r"活動時間|活动时间|活動期間|活动期间|參與時間|参与时间|event period|限時活動|限时活动",re.I)
MONEY=re.compile(r"累儲|累储|累充|儲值|充值|返利|首充|特惠礼包|特惠禮包|限時禮包|限时礼包|通行证|战令|戰令",re.I)
LIMITED=re.compile(r"限時|限时|福利|獎勵|奖励|禮包|礼包|聯動|联动|新服|开服|開服|签到|簽到|兑换码|兌換碼|活動|活动",re.I)

class TextLines(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg"):self.skip+=1
        if not self.skip and tag in ("p","div","li","br","h1","h2","h3","tr"):self.parts.append("\n")
    def handle_endtag(self,tag):
        if not self.skip and tag in ("p","div","li","h1","h2","h3","tr"):self.parts.append("\n")
        if tag in ("script","style","noscript","svg") and self.skip:self.skip-=1
    def handle_data(self,value):
        if not self.skip:self.parts.append(value)
    def lines(self):
        return [re.sub(r"\s+"," ",s).strip() for s in "".join(self.parts).splitlines() if s.strip()]

def normalized(name):
    return re.sub(r"[\W_]+","",str(name or "").casefold())
def exclude(name,config):
    key=normalized(name)
    return bool(key) and any(normalized(bad) in key for bad in config["excluded_games"])
def safe_taptap(url):
    try:
        u=urllib.parse.urlparse(url)
        return u.scheme=="https" and u.hostname in ("www.taptap.cn","taptap.cn") and (u.path.startswith("/moment/") or u.path.startswith("/app/"))
    except ValueError:return False
def fetch(url):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; GameIntelAdsRadar/1.0)",
        "Accept":"text/html,application/rss+xml,application/xml"})
    with urllib.request.urlopen(req,timeout=12) as response:
        if response.status!=200:raise RuntimeError("HTTP "+str(response.status))
        return response.read(1_000_001)[:1_000_000].decode("utf-8","replace")
def game_from_title(title):
    match=re.search(r"[《〈]([^》〉]{2,35})[》〉]",title)
    if match:return match.group(1).strip()
    # TapTap news headlines may not contain the game's name in a safe form.
    match=re.search(r"(?:- |｜)([^|｜-]{2,32})\s*(?:官方|论坛|TapTap)",title,re.I)
    return match.group(1).strip() if match else ""
def dated_ranges(lines):
    """Only accept an explicit same-line time range with two full years."""
    result=[]
    for line in lines:
        if not RANGE_MARKER.search(line):continue
        dates=list(DATE_RE.finditer(line[:260]))
        if len(dates)<2:continue
        try:
            first=dt.date(*map(int,dates[0].groups()))
            last=dt.date(*map(int,dates[1].groups()))
        except ValueError:continue
        if first>TODAY+dt.timedelta(days=365) or last<first or (last-first).days>120:continue
        result.append((first.isoformat(),last.isoformat(),line[:220]))
    return result

def candidate_from_taptap(url,title,raw,verified_at,game_hint=''):
    if not safe_taptap(url):return None
    parser=TextLines();parser.feed(raw)
    lines=parser.lines()
    # Captcha or blocked pages must never generate verified event claims.
    if (len(lines)<3 and len(" ".join(lines))<100) or any("arg1=" in x for x in lines[:3]):return None
    game=game_hint or game_from_title(title)
    if not game:return None
    ranges=dated_ranges(lines)
    if not ranges:return None
    a,b,text=ranges[0]
    category="累儲／儲值優惠" if MONEY.search(title+" "+text) else "遊戲限時活動"
    return {"game":game,"title":title[:155],"category":category,"market":"CN",
        "start_date":a,"end_date":b,"source_url":url,"source_type":"TapTap 文章日期擷取",
        "verified_at":verified_at,"detail":text,
        "evidence_status":"自動從公開文章擷取，未核實台服與活動資格"}

def google_news_url(query,lookback=14):
    # Read-only Google News RSS; this is NOT the complete Google Web Search API.
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q":query+" when:"+str(max(1,min(int(lookback),30)))+"d",
        "hl":"zh-TW","gl":"TW","ceid":"TW:zh-Hant"
    })

def google_discover(config,getter=fetch):
    """Discover relevant announcements across news domains, not just TapTap.

    A Google News item is *only a lead*. Its publication date is never used as
    an activity date, and Taiwan search locale does not establish TW eligibility.
    """
    general=config.get("google_news_queries",[])[:12]
    games=[x for x in config.get("google_priority_games",[]) if x and not exclude(x,config)][:35]
    hour=int(NOW.timestamp()//3600)
    count=int(config.get("google_general_queries_per_run",3))
    n_games=int(config.get("google_games_per_run",6))
    queries=[]
    if general:
        queries.extend((None,general[(hour+i)%len(general)]) for i in range(min(count,len(general))))
    if games:
        queries.extend((game,'"'+game.replace('"',"")+'" (活動 OR 限時 OR 儲值 OR 累儲 OR 禮包 OR 聯動 OR 開服)')
            for game in (games[(hour*n_games+i)%len(games)] for i in range(min(n_games,len(games)))))
    leads=[];errors=[];successful=0;items_seen=0
    days=int(config.get("google_news_lookback_days",14))
    for game,query in queries:
        url=google_news_url(query,days)
        try:
            root=ET.fromstring(getter(url))
            successful+=1
            for item in root.findall("./channel/item")[:40]:
                items_seen+=1
                title=(item.findtext("title") or "").strip()
                link=(item.findtext("link") or "").strip()
                description=(item.findtext("description") or "").strip()
                if not title or not LIMITED.search(title+" "+re.sub(r"<[^>]+>"," ",description[:250])):continue
                if not link.startswith("https://"):continue
                try:
                    link_host=urllib.parse.urlparse(link).hostname
                    if link_host not in ("news.google.com","google.com","www.google.com") and not link_host:continue
                except ValueError:continue
                # For a broad query, the named game must appear in the title.
                # For a targeted query, avoid wrong-game or generic results.
                mentioned=next((x for x in games if normalized(x) in normalized(title)),None)
                matched=game if game and normalized(game) in normalized(title) else mentioned
                if not matched:
                    quoted=game_from_title(title)
                    if quoted and not exclude(quoted,config):matched=quoted
                if not matched or exclude(matched,config):continue
                try:
                    published=email.utils.parsedate_to_datetime(item.findtext("pubDate") or "")
                    if published.tzinfo is None:published=published.replace(tzinfo=dt.timezone.utc)
                    if published<NOW-dt.timedelta(days=max(1,min(days,30))) or published>NOW+dt.timedelta(days=1):continue
                except (ValueError,TypeError,OverflowError):continue
                source=item.find("source")
                publisher=(source.text or "").strip() if source is not None else ""
                # Do not label an aggregator URL as official article verification.
                search_url="https://www.google.com/search?"+urllib.parse.urlencode({
                    "q":'"'+matched+'" "'+title[:110]+'"'
                })
                leads.append({
                    "game":matched,"title":title[:240],
                    "source_url":link,"google_search_url":search_url,
                    "published_at":published.isoformat(),
                    "publisher":publisher[:90],"source_type":"Google 新聞搜尋",
                    "verification_status":"公告搜尋線索，活動日期與台灣適用性尚未核實",
                    "status":"source_lead_only"
                })
        except Exception as e:
            errors.append({"provider":"Google News RSS","query":query[:100],"error":str(e)[:150]})
    dedup={}
    for lead in leads:
        key=normalized(lead["game"])+"|"+lead["source_url"]
        previous=dedup.get(key)
        if previous is None or lead["published_at"]>previous["published_at"]:dedup[key]=lead
    return list(dedup.values())[:110],len(queries),successful,items_seen,errors

def rss_discover(config,getter=fetch):
    sources=[];errors=[];checked=0
    for q in (config.get("taptap_discovery_queries",[])[:5] if config.get("taptap_supplement_enabled",True) else []):
        # Bing often supplies direct article URLs; Google may supply RSS redirect
        # URLs, which are ignored rather than falsely labeled as TapTap.
        for engine,url in (
          ("Bing Web","https://www.bing.com/search?"+urllib.parse.urlencode({"q":q,"format":"rss","setlang":"zh-hans"})),
          ("Google News","https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q+" when:14d","hl":"zh-CN","gl":"CN","ceid":"CN:zh-Hans"}))):
            checked+=1
            try:
                root=ET.fromstring(getter(url))
                for item in root.findall("./channel/item")[:25]:
                    link=(item.findtext("link") or "").strip()
                    title=(item.findtext("title") or "").strip()
                    if safe_taptap(link) and LIMITED.search(title):
                        sources.append({"url":link,"title":title,"via":engine})
            except Exception as e:errors.append({"provider":engine,"error":str(e)[:160]})
    # RSSHub's public documented TapTap forum route targets official posts.
    # China region restrictions may cause failures; never hide source errors.
    for item in (config.get("taptap_forum_feeds",[])[:8] if config.get("enable_taptap_rsshub",False) else []):
        game=str(item.get("game","")).strip()
        game_id=str(item.get("id",""))
        if not game or not re.fullmatch(r"\d{2,12}",game_id):continue
        checked+=1
        url="https://rsshub.app/taptap/topic/"+game_id+"/official"
        try:
            root=ET.fromstring(getter(url))
            for post in root.findall("./channel/item")[:15]:
                link=(post.findtext("link") or "").strip()
                title=(post.findtext("title") or "").strip()
                description=(post.findtext("description") or "")[:12000]
                named=game_from_title(title)
                # An official forum post must not be attributed to a different
                # title merely because it was found in that feed.
                if named and normalized(named)!=normalized(game):continue
                if safe_taptap(link) and LIMITED.search(title+" "+description[:450]):
                    sources.append({"url":link,"title":title,"description":description,
                        "via":"RSSHub official forum","game":game})
        except Exception as e:errors.append({"provider":"RSSHub "+game,"error":str(e)[:160]})
    unique={x["url"]:x for x in sources}
    chosen=sorted(unique.values(),key=lambda x:(x.get("via")!="RSSHub official forum",x["url"]))
    return chosen[:18],checked,errors

def evaluate(raw,config):
    row=dict(raw)
    game=row.get("game","").strip()
    if not game or exclude(game,config):return None
    a,b=str(row.get("start_date",""))[:10],str(row.get("end_date",""))[:10]
    try:
        start=dt.date.fromisoformat(a);end=dt.date.fromisoformat(b)
    except ValueError:return None
    if end<start:return None
    title=row.get("title","")
    money=bool(MONEY.search(title+" "+row.get("category","")+" "+row.get("signal","")))
    urgency=bool(LIMITED.search(title+" "+row.get("category","")))
    remaining=(end-TODAY).days
    direct=bool(row.get("source_url","").startswith("https://"))
    score=20+ (30 if money else 8 if urgency else 0)+15+ (8 if direct else 0)
    if 0<=remaining<=7:score+=15
    elif 7<remaining<=25:score+=8
    elif remaining<0:score-=35
    market=row.get("market","unknown").upper()
    if market=="TW":score+=12
    # Precise ad opportunity ratings must reflect regional applicability;
    # a China-only or unverified market cannot outrank verified TW leads.
    if market=="CN":score=min(score,48)
    elif market not in ("TW","GLOBAL"):score=min(score,55)
    score=max(0,min(100,score))
    if end<TODAY:status="已結束（歷史）"
    elif market=="CN":status="地區待核實（中國站）"
    elif market not in ("TW","GLOBAL"):status="地區與伺服器待核實"
    elif not direct:status="活動來源待核實"
    elif money:status="優先評估（需確認代儲資格）"
    else:status="資訊推廣候選"
    row["score"]=score
    row["status"]=status
    row["advertising_angle"]="儲值／禮包時效" if money else "活動資訊／玩家導流"
    row["market_label"]={"TW":"台灣","GLOBAL":"全球","CN":"中國站"}.get(market,"未知地區")
    row["updated_at"]=NOW.isoformat(timespec="seconds")
    row["id"]=hashlib.sha256((normalized(game)+"|"+title+"|"+a+"|"+b+"|"+row.get("source_url","")).encode()).hexdigest()[:24]
    row["recommendation_note"]="候選情報，不代表已核實投放權利、官方合作或代儲服務可用。"
    return row

def collect(config=None,previous=None,getter=fetch):
    config=config or json.loads(CFG.read_text(encoding="utf8"))
    old=previous or {"items":[]}
    rows=list(config.get("reference_events",[]))
    google_leads,google_checked,google_ok,google_seen,google_errors=google_discover(config,getter)
    candidates,checked,errors=rss_discover(config,getter)
    fetched=0;discovered=[]
    errors=google_errors+errors
    for lead in candidates:
        try:
            # Prefer the source's official forum RSS description, if complete,
            # before fetching a page that might be blocked by anti-crawler checks.
            content=lead.get("description") or ""
            cand=candidate_from_taptap(lead["url"],lead["title"],content,NOW.date().isoformat(),lead.get("game","")) if content else None
            if not cand:
                content=getter(lead["url"])
                cand=candidate_from_taptap(lead["url"],lead["title"],content,NOW.date().isoformat(),lead.get("game",""))
            if cand:
                if lead.get("via")=="RSSHub official forum":
                    cand["source_type"]="TapTap 官方版論壇 RSS"
                    cand["evidence_status"]="官方版論壇文字擷取，仍需核對地區與資格"
                rows.append(cand);fetched+=1
            else:discovered.append({"title":lead["title"],"source_url":lead["url"],"note":"頁面未取得可核實活動日期"})
        except Exception as e:
            discovered.append({"title":lead["title"],"source_url":lead["url"],"note":"TapTap 直接讀取失敗，保留來源線索"})
            errors.append({"provider":"TapTap page","error":str(e)[:160]})
    # Include otherwise-hidden dated events from all games, not only the owner's
    # two tracked games. A general news/event record is NOT assumed to be TW.
    for name in ("events","event_tips","tracked_events"):
        f=ROOT/"data"/(name+".json")
        if not f.exists():continue
        try:entries=json.loads(f.read_text(encoding="utf8")).get("items",[])
        except ValueError:continue
        for item in entries:
            x=dict(item)
            x["start_date"]=str(x.get("start_at") or x.get("start_date") or "")[:10]
            x["end_date"]=str(x.get("end_at") or x.get("end_date") or "")[:10]
            x["market"]=x.get("market") or "unknown"
            x["source_type"]=x.get("source_type") or (
                "已收錄遊戲活動" if name=="events" else
                "使用者提供截圖" if name=="event_tips" else
                "公開新聞追蹤活動")
            rows.append(x)
    merged={}
    for row in [*old.get("items",[]),*rows]:
        valid=evaluate(row,config)
        if valid:
            merged[valid["id"]]=valid
    items=sorted(merged.values(),key=lambda x:(x["end_date"]<TODAY.isoformat(),-x["score"],x["end_date"],x["game"]))
    # Preserve leads long enough for a later source verification pass. Never
    # promote them into dated events from the RSS publication timestamp.
    leads={}
    for lead in [*old.get("leads",[]),*google_leads,*discovered]:
        url=lead.get("source_url","")
        game=lead.get("game","")
        if not url or (game and exclude(game,config)):continue
        published=lead.get("published_at","")
        if published:
            try:
                stamp=dt.datetime.fromisoformat(published.replace("Z","+00:00"))
                if stamp<NOW-dt.timedelta(days=21):continue
            except (ValueError,TypeError):continue
        leads[url+"|"+game]=lead
    sorted_leads=sorted(leads.values(),key=lambda x:x.get("published_at",""),reverse=True)[:140]
    result={"updated_at":NOW.isoformat(timespec="seconds"),
        "items":items[:500],
        "leads":sorted_leads,
        "exclusions":"米哈遊／HoYoverse 旗下遊戲不進商機推薦",
        "note":"主要透過 Google 新聞搜尋探索跨站公告；搜尋命中不代表活動已核實。TapTap 僅為補充來源；不得把中國站活動當作台灣可投放活動。"}
    status={"updated_at":result["updated_at"],"queries_attempted":google_checked+checked,
        "google_queries_attempted":google_checked,"google_queries_succeeded":google_ok,
        "google_items_seen":google_seen,"google_leads_found_this_run":len(google_leads),
        "google_leads_in_history":sum(x.get("source_type")=="Google 新聞搜尋" for x in sorted_leads),
        "taptap_queries_attempted":checked,"taptap_article_links_found":len(candidates),
        "taptap_dated_items_parsed":fetched,
        "total_opportunities":len(items),"source_errors":errors[:30],
        "note":"Google News RSS 是公開新聞搜尋結果，不等於 Google 全網搜尋；活動公告須另外核實日期、遊戲與台灣伺服器適用性。"}
    return result,status

def main():
    prev=json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {"items":[]}
    old_status=json.loads(STATUS.read_text(encoding="utf8")) if STATUS.exists() else {}
    result,status=collect(previous=prev)
    # Avoid an hourly Cloudflare build when only the scan timestamp changed;
    # this keeps the no-subscription cloud design within free CI/build quotas.
    def facts(rows):
        return [{k:v for k,v in x.items() if k!="updated_at"} for x in rows]
    changed=(facts(result["items"])!=facts(prev.get("items",[]))
             or result["leads"]!=prev.get("leads",[]))
    if changed or not OUT.exists():
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    status_changed=(not STATUS.exists()
        or old_status.get("updated_at","")[:10]!=status["updated_at"][:10]
        or old_status.get("source_errors")!=status.get("source_errors")
        or old_status.get("taptap_dated_items_parsed")!=status.get("taptap_dated_items_parsed")
        or old_status.get("taptap_article_links_found")!=status.get("taptap_article_links_found")
        or old_status.get("google_queries_succeeded")!=status.get("google_queries_succeeded")
        or old_status.get("google_leads_found_this_run")!=status.get("google_leads_found_this_run"))
    if status_changed:
        STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Ad opportunity radar: "+json.dumps({k:v for k,v in status.items() if k!="source_errors"},ensure_ascii=False)+" changed="+str(changed))

if __name__=="__main__":main()
