#!/usr/bin/env python3
"""Build one-card-per-game, per-country Android/iOS data without false dates."""
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse,parse_qs

ROOT=Path(__file__).resolve().parents[1]
NOW=dt.datetime.now(dt.timezone.utc)
TODAY=NOW.date()
COUNTRIES={"TW":"台灣","US":"美國","JP":"日本","KR":"韓國","HK":"香港","SG":"新加坡"}
OUT=ROOT/"data/radar_catalog.json"
SOURCES=ROOT/"config/radar_sources.json"

def load(name):
    path=ROOT/"data"/(name+".json")
    try:return json.loads(path.read_text(encoding="utf8")) if path.exists() else {}
    except (ValueError,OSError):return {}

def clean(s):
    return re.sub(r"[\W_]+","",str(s or "").casefold(),flags=re.UNICODE)
def devkey(s):
    return re.sub(r"(incorporated|inc|company|limited|ltd|corp|co|studio|games|game|有限公司|股份有限公司|遊戲|游戏)$","",clean(s))
def releasedate(v):
    try:return dt.date.fromisoformat(str(v or "")[:10]).isoformat()
    except ValueError:return ""
def appid(url,store):
    p=urlparse(str(url or ""))
    if store=="Google Play":
        return parse_qs(p.query).get("id",[""])[0] if p.hostname=="play.google.com" else ""
    if p.hostname=="apps.apple.com":
        m=re.search(r"/id(\d+)",p.path)
        return m.group(1) if m else ""
    return ""
def url(store,ident,country):
    if store=="Google Play":
        return f"https://play.google.com/store/apps/details?id={ident}&hl=zh_TW&gl={country}"
    return f"https://apps.apple.com/{country.lower()}/app/id{ident}"
def platform(store):return "Android" if store=="Google Play" else "iOS"
def first_seen(v):
    return str(v or "")[:25]
def to_variant(raw,matrix=None):
    r=dict(raw)
    store=r.get("store") or (r.get("platforms") or [""])[0]
    if store not in ("App Store","Google Play"):return None
    country=str(r.get("country") or ("TW" if r.get("region")=="台灣" else "US")).upper()
    if country not in COUNTRIES:return None
    # Google Play uses only TW and the owner-designated US international market;
    # preserve broader Apple markets in the detailed iOS view.
    if store=="Google Play" and country not in ("TW","US"):return None
    key=r.get("app_id") or appid(r.get("source_url") or (r.get("store_links") or [{}])[0].get("url",""),store)
    if not key or not r.get("name"):return None
    matrix=matrix or {}
    source_date=releasedate(r.get("release_date") or matrix.get("country_launch_date") or matrix.get("store_release_date"))
    scope=r.get("date_scope") or r.get("date_label") or matrix.get("release_source_type") or matrix.get("store_release_date_scope") or ""
    is_pre=bool(r.get("preorder") or r.get("preorder_confirmed") or matrix.get("preorder_confirmed")
                or r.get("status") in ("預先註冊","預約"))
    if r.get("source_kind") in ("Play 官方商品頁","Apple Lookup"):
        is_pre=bool(r.get("preorder"))
    installable=bool(r.get("installable") or r.get("officially_installed"))
    if r.get("source_kind") in ("Play 官方商品頁","Apple Lookup"):
        installable=bool(r.get("installable"))
    # Never mistake a version update, catalog crawl date, or product-level
    # Apple date for a proven *country-first* launch date.
    date_verified=bool(source_date and (r.get("date_scope")=="官方發行日期"
       or matrix.get("country_launch_date") and matrix.get("country_launch_source")
       or store=="App Store" and (r.get("source_kind")=="Apple Lookup" or matrix.get("store_release_date"))))
    if is_pre:status="預先註冊" if store=="Google Play" else "預購"
    elif source_date and source_date>TODAY.isoformat():status="即將上市"
    elif installable or (source_date and source_date<=TODAY.isoformat()):status="已上市"
    else:status="商店有收錄"
    return {"id":key,"platform":platform(store),"store":store,"country":country,
      "country_name":COUNTRIES[country],"name":str(r.get("name") or "").strip(),
      "developer":str(r.get("developer") or matrix.get("developer") or "").strip(),
      "cover_url":r.get("cover_url") or matrix.get("cover_url") or "",
      "source_url":url(store,key,country),"status":status,
      "date":source_date if date_verified or (source_date and store=="App Store") else "",
      "date_scope":str(scope or ("Apple 產品發行日期，不代表此國首發" if store=="App Store" and source_date else "")),
      "country_launch_verified":bool(matrix.get("country_launch_date") and matrix.get("country_launch_source")),
      "first_seen_at":first_seen(r.get("first_seen_at") or matrix.get("first_seen_in_country_at")),
      "checked_at":r.get("last_checked_at") or matrix.get("checked_at") or "",
      "source_kind":r.get("source_kind") or "商店公開資料"}
def weight(r):
    return 5*(r.get("source_kind") in ("Play 官方商品頁","Apple Lookup"))+3*bool(r.get("date"))+2*bool(r.get("checked_at"))+bool(r.get("cover_url"))
def compact_aliases(names,base):
    out=[]
    seen={clean(base)}
    for name in names:
        name=str(name or "").strip()
        key=clean(name)
        if key and key not in seen and len(name)>=2:
            seen.add(key);out.append(name)
    return out[:12]

class DSU:
    def __init__(self):self.parent={}
    def find(self,x):
        if x not in self.parent:self.parent[x]=x
        if self.parent[x]!=x:self.parent[x]=self.find(self.parent[x])
        return self.parent[x]
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parent[max(a,b)]=min(a,b)

def build(catalog,matrix,discoveries,config,now=TODAY):
    bymatrix={}
    for x in matrix.get("items",[]):
        if x.get("platform") in ("Android","iOS") and x.get("app_id") and x.get("country") in COUNTRIES:
            bymatrix[(x["platform"],str(x["app_id"]),x["country"])]=x
    entries={}
    for raw in [*catalog.get("items",[]),*discoveries.get("items",[])]:
        store=raw.get("store") or (raw.get("platforms") or [""])[0]
        ident=raw.get("app_id") or appid(raw.get("source_url"),store)
        country=raw.get("country") or ("TW" if raw.get("region")=="台灣" else "US")
        m=bymatrix.get((platform(store),ident,country),{}) if store in ("Google Play","App Store") else {}
        item=to_variant(raw,m)
        if not item:continue
        key=(item["platform"],item["id"],item["country"])
        prev=entries.get(key)
        if prev:
            # Prefer the freshest official individual product check; preserve
            # earliest observation from either record.
            best=item if weight(item)>=weight(prev) else prev
            others=[x.get("first_seen_at") for x in (item,prev) if x.get("first_seen_at")]
            best["first_seen_at"]=min(others) if others else ""
            if not best.get("cover_url"):best["cover_url"]=prev.get("cover_url") or item.get("cover_url")
            entries[key]=best
        else:entries[key]=item
    # A release matrix row without a matching official catalog record cannot
    # independently prove that app was newly launched. Keep it out.
    variants=list(entries.values())
    dsu=DSU()
    group_for_id={}
    aliases={}
    for link in config.get("manual_identity_links",[]):
        anchor=None
        for store,ids in (("Android",link.get("android",[])),("iOS",link.get("ios",[]))):
            for ident in ids:
                key=f"{store}:{ident}"
                if anchor is not None:dsu.union(anchor,key)
                anchor=key
                group_for_id[key]=link["id"]
                aliases[key]=list(link.get("aliases",[]))
    # An app ID is a strong cross-country identity. Cross-OS automatic linking
    # requires BOTH a matching normalized title and matching publisher.
    candidates=defaultdict(set)
    for r in variants:
        key=f'{r["platform"]}:{r["id"]}'
        candidates[(clean(r["name"]),devkey(r["developer"]))].add(key)
    for (name,developer),keys in candidates.items():
        if not name or len(name)<4 or not developer or len(developer)<4:continue
        keys=sorted(keys)
        if len(keys)>1:
            for key in keys[1:]:dsu.union(keys[0],key)
    grouped=defaultdict(list)
    for v in variants:grouped[dsu.find(v["platform"]+":"+v["id"])].append(v)
    output=[]
    for key,rows in grouped.items():
        rows.sort(key=lambda x:(x["country"]!="TW",x["platform"]!="Android",x["country"],x["name"]))
        taiwan=[x for x in rows if x["country"]=="TW"]
        primary=(taiwan or rows)[0]
        # Prefer a Chinese official Taiwan name when available; else a Taiwan
        # official name regardless of script, else first known international name.
        name=next((r["name"] for r in taiwan if re.search(r"[\u3400-\u9fff]",r["name"])),primary["name"])
        alias_list=[x["name"] for x in rows if x["name"]!=name]
        for x in rows:alias_list.extend(aliases.get(f'{x["platform"]}:{x["id"]}',[]))
        alias_list=compact_aliases(alias_list,name)
        # Avoid showing a second essentially identical title in the overview.
        alt=next((a for a in alias_list if clean(a)!=clean(name) and
                   (bool(re.search(r"[\u3400-\u9fff]",a))!=bool(re.search(r"[\u3400-\u9fff]",name))
                    or len(a)>4 and len(name)>4 and clean(a)!=clean(name))),"")
        unique_countries={x["country"] for x in rows}
        recent=any(x["date"] and x["status"]=="已上市" and 0<=(now-dt.date.fromisoformat(x["date"])).days<=30
                   for x in rows if x["date"])
        upcoming=any(x["status"]=="即將上市" for x in rows)
        preorder=any(x["status"] in ("預購","預先註冊") for x in rows)
        categories=([ "新上市" ] if recent else [])+(["即將上市"] if upcoming else [])+(
                    ["預約／預先註冊"] if preorder else [])
        if not categories:categories=["全部遊戲"]
        relevant=[x["date"] for x in rows if x["date"] and x["status"] in ("即將上市","已上市")]
        earliest=min([x["first_seen_at"] for x in rows if x["first_seen_at"]],default="")
        latest=max([x["checked_at"] for x in rows if x["checked_at"]],default="")
        canonical_group=next((group_for_id.get(f'{v["platform"]}:{v["id"]}') for v in rows
                              if group_for_id.get(f'{v["platform"]}:{v["id"]}')),None)
        group_id=canonical_group or "radar-"+re.sub(r"[^0-9a-z]","",key.casefold())[:80]
        output.append({"id":group_id,"name":name,"other_name":alt,"aliases":alias_list,
           "developer":primary.get("developer") or next((x["developer"] for x in rows if x["developer"]),""),
           "cover_url":next((x["cover_url"] for x in rows if x["cover_url"]),""),
           "categories":categories,"country_count":len(unique_countries),
           "first_seen_at":earliest,"last_checked_at":latest,
           "date_sort":max(relevant,default=""),
           "variants":rows})
    output.sort(key=lambda x:(x.get("date_sort") or x.get("first_seen_at")[:10],x["name"]),reverse=True)
    health={"updated_at":NOW.isoformat(timespec="seconds"),
      "total_games":len(output),"total_store_variants":len(variants),
      "recent_30days":sum("新上市" in x["categories"] for x in output),
      "upcoming":sum("即將上市" in x["categories"] for x in output),
      "preregistration":sum("預約／預先註冊" in x["categories"] for x in output),
      "scope":"遊戲身份去重後統計，非各商店全球全部遊戲數"}
    return {"updated_at":NOW.isoformat(timespec="seconds"),
      "games":output,"note":"商店資訊經過商品 ID 與跨平台佐證合併；更新時間不等於首次上架時間"},health

def main():
    config=json.loads(SOURCES.read_text(encoding="utf8"))
    result,metrics=build(load("game_catalog"),load("release_matrix"),
                         load("radar_discoveries"),config)
    OUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf8")
    (ROOT/"data/radar_summary.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Radar snapshot:",json.dumps(metrics,ensure_ascii=False))
if __name__=="__main__":main()
