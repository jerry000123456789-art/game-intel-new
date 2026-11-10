#!/usr/bin/env python3
"""Collect publicly listed games; preserve history, dedupe by store app ID."""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
NOW=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
OUTPUT=ROOT/"data/game_catalog.json"
HEALTH=ROOT/"data/store_health.json"
SOURCES=[
    ("Google Play","台灣","https://play.google.com/store/games?hl=zh_TW&gl=TW"),
    ("Google Play","國際","https://play.google.com/store/games?hl=zh_TW&gl=US"),
    ("Google Play","國際","https://play.google.com/store/games?hl=ja&gl=JP"),
    ("Google Play","國際","https://play.google.com/store/games?hl=ko&gl=KR"),
    ("Google Play","台灣","https://play.google.com/store/apps/collection/promotion_3000000d51_pre_registration_games?hl=zh_TW&gl=TW"),
    ("Google Play","國際","https://play.google.com/store/apps/collection/promotion_3000000d51_pre_registration_games?hl=zh_TW&gl=US"),
    ("App Store","台灣","https://apps.apple.com/tw/iphone/games"),
    ("App Store","國際","https://apps.apple.com/us/iphone/games"),
    ("App Store","國際","https://apps.apple.com/jp/iphone/games"),
    ("App Store","國際","https://apps.apple.com/kr/iphone/games"),
    ("Huawei AppGallery","國際","https://appgallery.huawei.com/tab/automore%7Cdoublecolumncardwithstar%7C903189%7CA01000"),
]
MAX_HTML=5_000_000

class StoreLinks(HTMLParser):
    def __init__(self,platform):
        super().__init__(convert_charrefs=True)
        self.platform=platform
        self.current=None
        self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and self.current is None:
            href=a.get("href","")
            if (self.platform=="Google Play" and "/store/apps/details" in href and "id=" in href) or (
                self.platform=="App Store" and bool(re.search(r"/app/[^/?#]+/id\d+",href))):
                self.current={"href":href,"parts":[a.get("aria-label",""),a.get("title","")],"images":[]}
        elif self.current and tag in ("img","source"):
            if tag=="img":self.current["parts"].append(a.get("alt",""))
            raw=a.get("src","") or a.get("data-src","")
            if not raw and a.get("srcset"):
                raw=a["srcset"].split(",")[0].strip().split(" ")[0]
            if not raw and a.get("data-srcset"):
                raw=a["data-srcset"].split(",")[0].strip().split(" ")[0]
            if raw:self.current["images"].append(raw)
    def handle_data(self,data):
        if self.current:self.current["parts"].append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.current is not None:
            self.links.append(self.current)
            self.current=None

def country_from_link(platform, href, region):
    if platform=="Google Play":
        parsed=urllib.parse.urlparse(href)
        gl=urllib.parse.parse_qs(parsed.query).get("gl",[""])[0].upper()
        return gl if gl in ("TW","US","JP","KR","HK","SG") else ("TW" if region=="台灣" else "US")
    match=re.search(r"/(tw|us|jp|kr|hk|sg)/",urllib.parse.urlparse(href).path,re.I)
    return match.group(1).upper() if match else ("TW" if region=="台灣" else "US")

def normalized_link(platform,href,region,country=""):
    base="https://play.google.com" if platform=="Google Play" else "https://apps.apple.com"
    url=urllib.parse.urljoin(base,href)
    p=urllib.parse.urlparse(url)
    if platform=="Google Play":
        if p.hostname!="play.google.com":return ""
        appid=urllib.parse.parse_qs(p.query).get("id",[""])[0]
        if not re.fullmatch(r"[A-Za-z][\w.]{3,180}",appid):return ""
        return "https://play.google.com/store/apps/details?"+urllib.parse.urlencode({"id":appid,"hl":"zh_TW","gl":country or ("TW" if region=="台灣" else "US")})
    if p.hostname!="apps.apple.com":return ""
    found=re.search(r"/id(\d+)",p.path)
    country=country_from_link(platform,url,region)
    return "https://apps.apple.com/"+country.lower()+"/app/id"+found.group(1) if found else ""

def clean_title(raw):
    t=" ".join(str(raw or "").split()).strip("「」『』“”\" ")
    t=re.sub(r"\s*(?:[0-5](?:\.\d)?\s*star|\d+(?:\.\d)?\s*顆星).*$","",t,flags=re.I).strip()
    t=re.sub(r"(?:的)?(?:應用程式)?(?:圖示|縮圖|螢幕截圖)圖片$","",t).strip("「」『』“”\" ")
    if t.casefold() in ("圖片","圖示","縮圖","螢幕截圖","照片","遊戲","檢視","icon","image","screenshot"):return ""
    if len(t)<2 or len(t)>95 or t.count(",")>=3:return ""
    if t.startswith("https://") or re.fullmatch(r"\d+[\d,.]*",t):return ""
    return t

def title_for(platform,candidates):
    for raw in candidates:
        title=clean_title(raw)
        if title:return title
    return ""

def verified_cover(raw,platform):
    raw=str(raw or '').replace('&amp;','&').strip()
    if raw.startswith('//'):raw='https:'+raw
    parsed=urllib.parse.urlparse(raw)
    if parsed.scheme!='https':return ''
    host=(parsed.hostname or '').lower()
    if platform=='Google Play' and (host=='play-lh.googleusercontent.com' or host=='lh3.googleusercontent.com'):
        return raw[:1200]
    if platform=='App Store' and (re.fullmatch(r'is[0-9]+-ssl.mzstatic.com',host) or re.fullmatch(r'is[0-9]+.mzstatic.com',host) or host=='is1-ssl.mzstatic.com'):
        return raw[:1200]
    return ''

def parse_store(html,platform,region,country=""):
    p=StoreLinks(platform)
    p.feed(html)
    result={}
    for row in p.links:
        link=normalized_link(platform,row["href"],region,country)
        title=title_for(platform,row["parts"])
        if not link or not title:continue
        if link not in result:
            country=country_from_link(platform,link,region)
            artwork=next((v for raw in row.get("images",[]) if (v:=verified_cover(raw,platform))),"")
            result[link]={
                "id":hashlib.sha256((platform+"|"+region+"|"+link).encode()).hexdigest()[:22],
                "name":title,"status":"商店收錄","region":region,"country":country,"platforms":[platform],
                "release_date":"","developer":"","cover_url":artwork,
                "store_links":[{"name":platform,"url":link,"region":region}],
                "payment_methods":[],"source_url":link,"verified_store_listing":True,
                "first_seen_at":NOW,
            }
    return list(result.values())

def catalog_key(row):
    platform=(row.get("platforms") or [""])[0]
    region="國際" if row.get("region")=="美國" else row.get("region","")
    link=row.get("source_url","") or (row.get("store_links") or [{}])[0].get("url","")
    p=urllib.parse.urlparse(link)
    if p.hostname=="play.google.com":
        appid=urllib.parse.parse_qs(p.query).get("id",[""])[0]
        if appid:return (platform,country_from_link(platform,link,region),"play:"+appid.casefold())
    if p.hostname=="apps.apple.com":
        m=re.search(r"/id(\d+)",p.path)
        if m:return (platform,country_from_link(platform,link,region),"apple:"+m.group(1))
    if p.hostname=="store.steampowered.com":
        m=re.search(r"/app/(\d+)",p.path)
        if m:return (platform,region,"steam:"+m.group(1))
    return (platform,row.get("country") or region,"name:"+clean_title(row.get("name","")).casefold())

def catalog_quality(row):
    return sum(bool(row.get(k)) for k in ("developer","cover_url","release_date","seed_method")) + 2*int(row.get("status") in ("即將上市","已上市","預先註冊"))

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; GameIntelPublicListing/1.0)","Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req,timeout=22) as resp:
        if resp.status!=200:raise RuntimeError("HTTP "+str(resp.status))
        raw=resp.read(MAX_HTML+1)
        if len(raw)>MAX_HTML:raise RuntimeError("response exceeds 5 MB")
        return raw.decode("utf-8","replace")

def run():
    data=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"items":[]}
    old=data.get("items",[])
    merged={}
    for row in old:
        if not any(p in ("App Store","Google Play") for p in row.get("platforms",[])):continue
        name=clean_title(row.get("name",""))
        if not name:continue
        x=dict(row)
        x["name"]=name
        if x.get("region")=="美國":
            x["region"]="國際"
            for st in x.get("store_links",[]):
                if st.get("region")=="美國":st["region"]="國際"
        x["country"]=x.get("country") or country_from_link((x.get("platforms") or [""])[0],x.get("source_url",""),x.get("region",""))
        key=catalog_key(x)
        if key not in merged or catalog_quality(x)>catalog_quality(merged[key]):merged[key]=x
    previous=json.loads(HEALTH.read_text(encoding="utf-8")) if HEALTH.exists() else {"sources":{}}
    health=previous.get("sources",{})
    fresh=0
    for platform,region,url in SOURCES:
        country=country_from_link(platform,url,region)
        is_pre_registration="promotion_3000000d51_pre_registration_games" in url
        source_name=platform+(" 預先註冊 " if is_pre_registration else " ")+country
        state=health.get(source_name,{})
        try:
            if platform=="Huawei AppGallery":
                page=fetch(url)
                raise RuntimeError("官網需 JavaScript 動態載入，目前無可核對清單（"+str(len(page))+" bytes）")
            listings=parse_store(fetch(url),platform,region,country)
            if not listings:raise RuntimeError("頁面未取得有效遊戲連結")
            for x in listings:
                if is_pre_registration:
                    # This curated list signals pre-registration, not a confirmed launch date.
                    x["status"]="預先註冊"
                    x["pre_registration_collection_url"]=url
                    x["pre_registration_collection_seen_at"]=NOW
                key=catalog_key(x)
                if key in merged:
                    prior=merged[key]
                    x["id"]=prior.get("id") or x["id"]
                    x["first_seen_at"]=prior.get("first_seen_at") or prior.get("discovered_at") or NOW
                    for field in ("release_date","developer","cover_url","payment_methods","seed_method"):
                        x[field]=prior.get(field) or x.get(field) or ([] if field=="payment_methods" else "")
                    if prior.get("status") not in ("商店收錄","已上市","") and not is_pre_registration:
                        x["status"]=prior["status"]
                    x["pre_registration_collection_seen_at"]=x.get("pre_registration_collection_seen_at") or prior.get("pre_registration_collection_seen_at","")
                    x["pre_registration_collection_url"]=x.get("pre_registration_collection_url") or prior.get("pre_registration_collection_url","")
                    if catalog_quality(prior)>=catalog_quality(x):
                        x["name"]=prior["name"]
                else:
                    fresh+=1
                merged[key]=x
            state={"state":"success","last_checked_at":NOW,"last_success_at":NOW,
                   "items_this_run":len(listings),"source_url":url}
        except Exception as error:
            state={"state":"error","last_checked_at":NOW,
                   "last_success_at":state.get("last_success_at",""),
                   "items_this_run":0,"error":str(error)[:220],"source_url":url}
        health[source_name]=state
        print(source_name+": "+state["state"]+", items="+str(state["items_this_run"])+(" ERROR "+state.get("error","") if state["state"]=="error" else ""))
    records=list(merged.values())
    records.sort(key=lambda x:(x.get("first_seen_at",""),x.get("release_date","")),reverse=True)
    if records!=old:
        data["items"]=records
        data["updated_at"]=NOW
        data["note"]="商店收錄日期不等於遊戲上市日期；遊戲名稱去除圖片文字並依商店 ID 去重。"
        OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    HEALTH.write_text(json.dumps({"updated_at":NOW,"sources":health},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Store catalog: total="+str(len(records))+" newly_added="+str(fresh))
    return fresh

if __name__=="__main__":run()
