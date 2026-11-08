#!/usr/bin/env python3
"""Enrich mobile game listings using each official app page; no Steam.

Populate actual store artwork, precise platform status when supportable,
official release/publication date separately from update/first-seen.
Never treat an app listing crawl or an update date as a first release.
"""
import concurrent.futures as futures
import datetime as dt
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"data/game_catalog.json"
MATRIX=ROOT/"data/release_matrix.json"
STATUS=ROOT/"data/mobile_enrichment_status.json"
NOW=dt.datetime.now(dt.timezone.utc)
TODAY=NOW.date()
MAX_ANDROID=180
CONCURRENT=10

class PageFacts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cover=""
        self.ld=[]
        self.inscript=""
        self.script=False
        self.parts=[]
        self.button_depth=0
        self.buttons=[]
        self.current_button=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="meta":
            key=(a.get("property") or a.get("name") or "").lower()
            if key in ("og:image","twitter:image","twitter:image:src") and not self.cover:
                self.cover=a.get("content","")
        elif tag=="script" and a.get("type","").lower()=="application/ld+json":
            self.script=True;self.inscript=""
        elif tag=="button":
            self.button_depth+=1
            if self.button_depth==1:self.current_button=[]
    def handle_data(self,data):
        if self.script:self.inscript+=data
        elif self.button_depth:self.current_button.append(data)
        elif data.strip():self.parts.append(data.strip())
    def handle_endtag(self,tag):
        if tag=="script" and self.script:
            self.script=False
            if self.inscript and len(self.inscript)<200_000:
                try:self.ld.append(json.loads(self.inscript))
                except ValueError:pass
        elif tag=="button" and self.button_depth:
            self.button_depth-=1
            if self.button_depth==0:
                self.buttons.append(" ".join(self.current_button).strip())

def official_art(url):
    url=html.unescape(str(url or "").strip())
    if url.startswith("//"):url="https:"+url
    parsed=urllib.parse.urlparse(url)
    host=(parsed.hostname or "").lower()
    if parsed.scheme!="https" or len(url)>2000:return ""
    if host in ("play-lh.googleusercontent.com","lh3.googleusercontent.com") or re.fullmatch(r"is[0-9]+(?:-ssl)?\.mzstatic\.com",host):
        return url
    return ""

def date_only(raw):
    text=str(raw or "").strip()
    if len(text)>=10 and re.match(r"^\d{4}-\d\d-\d\d",text):
        try:return dt.date.fromisoformat(text[:10]).isoformat()
        except ValueError:pass
    for fmt in ("%b %d, %Y","%B %d, %Y","%d %b %Y","%d %B %Y"):
        try:return dt.datetime.strptime(text[:25],fmt).date().isoformat()
        except ValueError:pass
    return ""

def released_from_text(parser):
    text=[html.unescape(s).strip() for s in parser.parts]
    for i,s in enumerate(text):
        # Must say 'Released on' or its exact locale equivalent; NEVER 'Updated on'.
        match=re.fullmatch(r"(?:Released on|發佈日期|發布日期|首次推出日期|公開日|リリース日|출시일)",s,re.I)
        if not match:continue
        for candidate in text[i+1:i+4]:
            if len(candidate)>40:continue
            date=date_only(candidate)
            if date:return date
    return ""

def metadata_from_html(raw):
    p=PageFacts();p.feed(raw)
    result={"cover_url":official_art(p.cover),"store_release_date":"","version_release_date":"",
            "preorder_confirmed":False,"officially_installed":False,
            "release_source_type":"","checked_at":NOW.isoformat(timespec="seconds")}
    for ld in p.ld:
        stack=ld if isinstance(ld,list) else [ld]
        while stack:
            item=stack.pop()
            if not isinstance(item,dict):continue
            if item.get("@graph") and isinstance(item["@graph"],list):
                stack.extend(item["@graph"])
            typ=item.get("@type","")
            if isinstance(typ,list):typ=" ".join(typ)
            if not any(x in str(typ) for x in ("SoftwareApplication","MobileApplication","VideoGame")):continue
            image=item.get("image") or item.get("thumbnailUrl")
            if isinstance(image,dict):image=image.get("url","")
            if isinstance(image,list):image=image[0] if image else ""
            if not result["cover_url"]:result["cover_url"]=official_art(image)
            release=date_only(item.get("datePublished"))
            if release:result["store_release_date"]=release;result["release_source_type"]="Google Play 結構化發行日期"
            offers=item.get("offers",{})
            if isinstance(offers,list):offers=offers[0] if offers else {}
            if not isinstance(offers,dict):offers={}
            availability=str(offers.get("availability",""))
            if "PreOrder" in availability:result["preorder_confirmed"]=True
            elif "InStock" in availability:result["officially_installed"]=True
    if not result["store_release_date"]:
        release=released_from_text(p)
        if release:result["store_release_date"]=release;result["release_source_type"]="Google Play Released on"
    # Button text is only accepted as preorder when literally an actionable label.
    if any(re.fullmatch(r"(?:Pre-register|預先註冊|事前登録|사전 등록)",x,re.I) for x in p.buttons):
        result["preorder_confirmed"]=True
    if any(re.fullmatch(r"(?:Install|安裝|インストール|설치|Buy|購買)",x,re.I) for x in p.buttons):
        result["officially_installed"]=True
    if result["preorder_confirmed"]:result["officially_installed"]=False
    return result

def status_for(release_date="",preorder=False,installable=False):
    if preorder:return "預先註冊"
    try:release=dt.date.fromisoformat(str(release_date)[:10])
    except ValueError:release=None
    if release and release>TODAY:return "即將上市"
    if release and (TODAY-release).days<=30:return "新上市"
    if release:return "已上市"
    if installable:return "已上市"
    return "商店收錄"

def android_id(row):
    u=row.get("source_url","")
    try:
        parsed=urllib.parse.urlparse(u)
        if parsed.hostname!="play.google.com":return ""
        return urllib.parse.parse_qs(parsed.query).get("id",[""])[0]
    except ValueError:return ""

def valid_cover_for_row(url):
    return official_art(url)

def enrich(catalog,matrix,lookup=None,max_android=MAX_ANDROID):
    """Pure-transform catalogs. lookup(row) returns metadata parsed from app page."""
    rows=[dict(x) for x in catalog.get("items",[]) if any(p in ("Google Play","App Store") for p in x.get("platforms",[]))]
    original_matrix=[dict(x) for x in matrix.get("items",[])]
    by_key={(x.get("platform"),x.get("app_id"),x.get("country")):x for x in original_matrix}
    checked=set()
    for x in rows:
        p=x["platforms"][0]
        if p=="Google Play":
            appid=android_id(x)
            country=str(x.get("country") or "TW" if x.get("region")=="台灣" else x.get("country") or "US").upper()
            if not appid:continue
            k=("Android",appid,country)
            obs=by_key.get(k)
            if obs is None:
                obs={"platform":"Android","app_id":appid,"country":country,
                     "country_name":{"TW":"台灣","US":"美國","JP":"日本","KR":"韓國","HK":"香港","SG":"新加坡"}.get(country,country),
                     "availability":"商店目錄已收錄","first_seen_in_country_at":x.get("first_seen_at",""),
                     "store_release_date":"","country_launch_date":"","source_url":x.get("source_url","")}
                by_key[k]=obs
            if not x.get("cover_url") and obs.get("cover_url"):x["cover_url"]=obs["cover_url"]
            if obs.get("store_release_date"):x["release_date"]=obs["store_release_date"]
            x["status"]=status_for(obs.get("store_release_date") or x.get("release_date",""),
                obs.get("preorder_confirmed",False),obs.get("officially_installed",False))
        elif p=="App Store":
            import re
            link=x.get("source_url","")
            m=re.search(r"/id(\d+)",urllib.parse.urlparse(link).path)
            if not m:continue
            country=str(x.get("country") or ("TW" if x.get("region")=="台灣" else "US")).upper()
            obs=by_key.get(("iOS",m.group(1),country),{})
            if obs.get("availability")=="商店有收錄":
                x["status"]=status_for(obs.get("store_release_date",""),obs.get("preorder_confirmed",False),True)
            elif x.get("release_date"):
                x["status"]=status_for(x["release_date"])
            else:x["status"]="商店收錄"
            if obs.get("store_release_date"):x["release_date"]=obs["store_release_date"]
            if not x.get("cover_url") and obs.get("cover_url"):x["cover_url"]=obs["cover_url"]
            if not x.get("developer") and obs.get("developer"):x["developer"]=obs["developer"]
        x["cover_url"]=valid_cover_for_row(x.get("cover_url",""))
    # Pick Android apps needing images or metadata; oldest checked first so all eventually get audited.
    candidates=[]
    for x in rows:
        if x.get("platforms",[""])[0]!="Google Play" or not android_id(x):continue
        c=str(x.get("country") or ("TW" if x.get("region")=="台灣" else "US")).upper()
        k=("Android",android_id(x),c)
        if k in checked:continue
        checked.add(k)
        obs=by_key.get(k,{})
        priority=(0 if not x.get("cover_url") else 1,
                  obs.get("metadata_checked_at",""),x.get("first_seen_at",""))
        candidates.append((priority,k,x))
    candidates.sort(key=lambda r:r[0])
    selected=candidates[:max_android]
    def official_lookup(item):
        _,key,row=item
        if lookup is not None:return key,lookup(row)
        url=row.get("source_url","")
        if not url:raise RuntimeError("Missing official listing")
        parsed=urllib.parse.urlparse(url)
        q=urllib.parse.parse_qs(parsed.query)
        q["hl"]=["en_US"]
        req=urllib.request.Request(urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(q,doseq=True))),
            headers={"User-Agent":"Mozilla/5.0 (compatible; GameIntelStoreEvidence/1.0)","Accept":"text/html"})
        with urllib.request.urlopen(req,timeout=12) as resp:
            if resp.status!=200:raise RuntimeError("Google Play HTTP "+str(resp.status))
            html_doc=resp.read(1800000).decode("utf-8","replace")
        return key,metadata_from_html(html_doc)
    succeeded=0;failures=[]
    with futures.ThreadPoolExecutor(max_workers=CONCURRENT) as pool:
        work={pool.submit(official_lookup,item):item for item in selected}
        for job in futures.as_completed(work):
            try:
                k,metadata=job.result()
                obs=by_key[k]
                for field in ("cover_url","store_release_date","release_source_type"):
                    if metadata.get(field):obs[field]=metadata[field]
                obs["metadata_checked_at"]=metadata["checked_at"]
                obs["preorder_confirmed"]=metadata.get("preorder_confirmed",False)
                obs["officially_installed"]=metadata.get("officially_installed",False)
                succeeded+=1
            except Exception as e:
                failures.append(str(e)[:140])
    # Reapply newly collected official artwork and dates.
    for x in rows:
        if x.get("platforms",[""])[0]!="Google Play":continue
        c=str(x.get("country") or ("TW" if x.get("region")=="台灣" else "US")).upper()
        obs=by_key.get(("Android",android_id(x),c),{})
        if not x.get("cover_url") and obs.get("cover_url"):x["cover_url"]=valid_cover_for_row(obs["cover_url"])
        if obs.get("store_release_date"):x["release_date"]=obs["store_release_date"]
        x["status"]=status_for(obs.get("store_release_date") or x.get("release_date",""),
            obs.get("preorder_confirmed",False),obs.get("officially_installed",False))
    matrix["items"]=sorted(by_key.values(),key=lambda a:(a.get("name",""),a.get("platform",""),a.get("country","")))
    catalog["items"]=rows
    counts={}
    for x in rows:counts[x["status"]]=counts.get(x["status"],0)+1
    status={"updated_at":NOW.isoformat(timespec="seconds"),"android_checked":len(selected),
        "android_success":succeeded,"android_failures":len(failures),
        "images":sum(bool(x.get("cover_url")) for x in rows),
        "items":len(rows),"status_counts":counts,"errors":failures[:20],
        "note":"首發日期僅使用來源明確欄位，不把版本更新及本站收錄日當作上架日。"}
    return catalog,matrix,status

def run():
    catalog=json.loads(CATALOG.read_text(encoding="utf8"))
    matrix=json.loads(MATRIX.read_text(encoding="utf8")) if MATRIX.exists() else {"items":[]}
    cat,mat,health=enrich(catalog,matrix)
    CATALOG.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    MATRIX.write_text(json.dumps(mat,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    STATUS.write_text(json.dumps(health,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Mobile game evidence:",json.dumps(health,ensure_ascii=False))

if __name__=="__main__":run()
