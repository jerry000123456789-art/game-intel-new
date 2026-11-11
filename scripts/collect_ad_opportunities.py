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

def candidate_from_taptap(url,title,raw,verified_at):
    if not safe_taptap(url):return None
    parser=TextLines();parser.feed(raw)
    lines=parser.lines()
    # Captcha or blocked pages must never generate verified event claims.
    if len(lines)<3 or any("arg1=" in x for x in lines[:3]):return None
    game=game_from_title(title)
    if not game:return None
    ranges=dated_ranges(lines)
    if not ranges:return None
    a,b,text=ranges[0]
    category="累儲／儲值優惠" if MONEY.search(title+" "+text) else "遊戲限時活動"
    return {"game":game,"title":title[:155],"category":category,"market":"CN",
        "start_date":a,"end_date":b,"source_url":url,"source_type":"TapTap 文章日期擷取",
        "verified_at":verified_at,"detail":text,
        "evidence_status":"自動從公開文章擷取，未核實台服與活動資格"}

def rss_discover(config,getter=fetch):
    sources=[];errors=[];checked=0
    for q in config.get("taptap_discovery_queries",[])[:5]:
        # Bing often supplies direct article URLs; Google may supply RSS redirect
        # URLs, which are ignored rather than falsely labeled as TapTap.
        for engine,url in (
          ("Bing","https://www.bing.com/news/search?"+urllib.parse.urlencode({"q":q,"format":"rss","mkt":"zh-CN"})),
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
    unique={x["url"]:x for x in sources}
    return list(unique.values())[:12],checked,errors

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
    candidates,checked,errors=rss_discover(config,getter)
    fetched=0;discovered=[]
    for lead in candidates:
        try:
            content=getter(lead["url"])
            cand=candidate_from_taptap(lead["url"],lead["title"],content,NOW.date().isoformat())
            if cand:
                rows.append(cand);fetched+=1
            else:discovered.append({"title":lead["title"],"source_url":lead["url"],"note":"頁面未取得可核實活動日期"})
        except Exception as e:
            discovered.append({"title":lead["title"],"source_url":lead["url"],"note":"TapTap 直接讀取失敗，保留來源線索"})
            errors.append({"provider":"TapTap page","error":str(e)[:160]})
    # Include otherwise-hidden dated events from all games, not only the owner's
    # two tracked games. A general news/event record is NOT assumed to be TW.
    for name in ("events","event_tips"):
        f=ROOT/"data"/(name+".json")
        if not f.exists():continue
        try:entries=json.loads(f.read_text(encoding="utf8")).get("items",[])
        except ValueError:continue
        for item in entries:
            x=dict(item)
            x["start_date"]=str(x.get("start_at") or x.get("start_date") or "")[:10]
            x["end_date"]=str(x.get("end_at") or x.get("end_date") or "")[:10]
            x["market"]=x.get("market") or "unknown"
            x["source_type"]=x.get("source_type") or ("已收錄遊戲活動" if name=="events" else "使用者提供截圖")
            rows.append(x)
    merged={}
    for row in [*old.get("items",[]),*rows]:
        valid=evaluate(row,config)
        if valid:
            merged[valid["id"]]=valid
    items=sorted(merged.values(),key=lambda x:(x["end_date"]<TODAY.isoformat(),-x["score"],x["end_date"],x["game"]))
    result={"updated_at":NOW.isoformat(timespec="seconds"),
        "items":items[:500],
        "leads":discovered[:80],
        "exclusions":"米哈遊／HoYoverse 旗下遊戲不進商機推薦",
        "note":"中國 TapTap 活動僅作商機線索；必須核實台灣服參加條件、商業服務能力與廣告規則。"}
    status={"updated_at":result["updated_at"],"queries_attempted":checked,
        "taptap_article_links_found":len(candidates),"taptap_dated_items_parsed":fetched,
        "total_opportunities":len(items),"source_errors":errors[:30],
        "note":"RSS 可能未索引 TapTap；防爬或驗證頁阻擋不會被當作成功收集。"}
    return result,status

def main():
    prev=json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {"items":[]}
    result,status=collect(previous=prev)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Ad opportunity radar: "+json.dumps({k:v for k,v in status.items() if k!="source_errors"},ensure_ascii=False))

if __name__=="__main__":main()
