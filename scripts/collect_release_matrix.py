#!/usr/bin/env python3
"""Country/OS storefront snapshots. Do not mistake app updates for first launches.

Apple releaseDate is an App Store product-level date; NOT a verified country
launch date. Country visibility and first observed dates are stored separately.
Google Play listing appearance similarly never proves first launch time.
"""
import datetime as dt
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"data/game_catalog.json"
OUTPUT=ROOT/"data/release_matrix.json"
STATUS=ROOT/"data/release_matrix_status.json"
NOW=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
COUNTRIES={"TW":"台灣","US":"美國","JP":"日本","KR":"韓國","HK":"香港","SG":"新加坡"}
MAX_IOS_IDS=6    # 6 app ids x 6 storefront countries per run, rotated
MIN_APPLE_INTERVAL=3.1

def apple_id_from_link(url):
    match=re.search(r"/id(\d+)",urllib.parse.urlparse(url).path)
    return match.group(1) if match else ""

def play_id_from_link(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.hostname!="play.google.com":return ""
    return urllib.parse.parse_qs(parsed.query).get("id",[""])[0]

def date_only(value):
    s=str(value or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",s):return ""
    try:dt.date.fromisoformat(s)
    except ValueError:return ""
    return s

def fetch_apple(app_id,country):
    query=urllib.parse.urlencode({"id":app_id,"country":country.lower()})
    req=urllib.request.Request("https://itunes.apple.com/lookup?"+query,
         headers={"User-Agent":"GameIntelReleaseMatrix/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=14) as response:
        if response.status!=200:raise RuntimeError("Apple HTTP "+str(response.status))
        return json.load(response)

def apple_row(app_id,country,data,previous=None):
    previous=previous or {}
    results=[x for x in data.get("results",[]) if str(x.get("trackId",""))==app_id and x.get("kind")=="software"]
    if not results:
        # API resultCount=0 is inconclusive, never label as unavailable.
        return {**previous,"platform":"iOS","store":"App Store","app_id":app_id,"country":country,
          "country_name":COUNTRIES[country],"availability":"未確認","checked_at":NOW,
          "note":"此國 Apple Lookup 未回傳該遊戲；不代表確定尚未上市"}
    app=results[0]
    first=previous.get("first_seen_in_country_at") or NOW
    return {**previous,"platform":"iOS","store":"App Store","app_id":app_id,
        "country":country,"country_name":COUNTRIES[country],"name":app.get("trackName",""),
        "availability":"商店有收錄","first_seen_in_country_at":first,
        "store_release_date":date_only(app.get("releaseDate")),
        "store_release_date_scope":"Apple 產品 releaseDate，非該國首次上市日期",
        "country_launch_date":previous.get("country_launch_date",""),
        "country_launch_source":previous.get("country_launch_source",""),
        "version_release_date":date_only(app.get("currentVersionReleaseDate")),
        "source_url":app.get("trackViewUrl") or "https://apps.apple.com/"+country.lower()+"/app/id"+app_id,
        "checked_at":NOW,
        "note":"商店可見≠各國正式上市日；版本日期不作上市日"}

def catalog_ids(items):
    ids={}
    for row in items:
        if "App Store" not in row.get("platforms",[]):continue
        urls=[row.get("source_url","")]+[x.get("url","") for x in row.get("store_links",[])]
        app_id=next((v for u in urls if (v:=apple_id_from_link(u))),"")
        if not app_id:continue
        if app_id not in ids:ids[app_id]=row.get("name","")
    return ids

def android_rows(catalog,old_rows):
    result=[]
    for row in catalog:
        if "Google Play" not in row.get("platforms",[]):continue
        urls=[row.get("source_url","")]+[x.get("url","") for x in row.get("store_links",[])]
        app_id=next((v for u in urls if (v:=play_id_from_link(u))),"")
        if not app_id:continue
        region=row.get("region","台灣")
        country=str(row.get("country") or ("TW" if region=="台灣" else "US")).upper()
        if country not in COUNTRIES:country="TW" if region=="台灣" else "US"
        key=("Android",app_id,country)
        prev=old_rows.get(key,{})
        result.append({**prev,"platform":"Android","store":"Google Play","app_id":app_id,
             "country":country,"country_name":COUNTRIES[country],
             "name":row.get("name",""),"availability":"商店目錄已收錄",
             "first_seen_in_country_at":prev.get("first_seen_in_country_at") or row.get("first_seen_at") or NOW,
             "store_release_date":prev.get("store_release_date",""),"country_launch_date":prev.get("country_launch_date",""),
             "country_launch_source":prev.get("country_launch_source",""),
             "version_release_date":prev.get("version_release_date",""),
             "release_source_type":prev.get("release_source_type",""),
             "source_url":row.get("source_url",""),
             "checked_at":NOW,"note":"商店目錄收錄不等於首次上架。Android 原始上市日期需官方或歷史資料佐證。"})
    return result

def generate(catalog,old=None,fetch=fetch_apple,limit=MAX_IOS_IDS,sleep=time.sleep):
    old=old or {"items":[],"checked_ids":{}}
    merged={(x.get("platform"),x.get("app_id"),x.get("country")):x for x in old.get("items",[])}
    for x in android_rows(catalog,merged):
        merged[(x["platform"],x["app_id"],x["country"])]=x
    ids=catalog_ids(catalog)
    checked=dict(old.get("checked_ids",{}))
    selected=sorted(ids, key=lambda app_id:(checked.get(app_id,""),app_id))[:limit]
    succeeded=0; failed=0; failures=[]
    for index,app_id in enumerate(selected):
        complete=True
        for country in COUNTRIES:
            try:
                data=fetch(app_id,country)
                key=("iOS",app_id,country)
                merged[key]=apple_row(app_id,country,data,merged.get(key))
                succeeded+=1
            except Exception as error:
                failed+=1;complete=False
                failures.append({"app_id":app_id,"country":country,"message":str(error)[:170]})
            if fetch is fetch_apple:sleep(MIN_APPLE_INTERVAL)
        if complete:checked[app_id]=NOW
    records=sorted(merged.values(),key=lambda x:(x.get("name",""),x.get("platform",""),x.get("country","")))
    result={"updated_at":NOW,"items":records,"checked_ids":checked,
            "note":"Android/iOS 與國家分開。首次在該國觀察到≠該國上架日；Apple releaseDate≠該國首發日；currentVersionReleaseDate 是版本更新日。"}
    status={"updated_at":NOW,"ios_ids_this_run":len(selected),"ios_countries_checked":succeeded,
            "failed_checks":failed,"platform_entries":len(records),"errors":failures[:30]}
    return result,status

def run():
    catalog=json.loads(CATALOG.read_text(encoding="utf-8")).get("items",[])
    old=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    result,status=generate(catalog,old)
    # Keep existing fields and snapshots on temporary source failures.
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Release matrix: "+json.dumps(status,ensure_ascii=False))

if __name__=="__main__":run()
