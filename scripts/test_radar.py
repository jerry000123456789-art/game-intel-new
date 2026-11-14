#!/usr/bin/env python3
"""Offline regression for scoped release dates, game identity and all 4 misses."""
import datetime as dt
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/(name+".py"))
 import sys
 sys.path.insert(0,str(ROOT/"scripts"))
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m
collector=module("collect_radar")
builder=module("build_radar")
cfg=json.loads((ROOT/"config/radar_sources.json").read_text(encoding="utf8"))
seed_ids={x["id"] for x in cfg["direct_google_ids"]}
assert {"com.azragames.ungodly","com.looperse.td3kingdom","com.jiys.mfqb","com.curiousdotlab.level99"}<=seed_ids
assert cfg["google_markets"]==["TW","US"],"Google Play must use Taiwan and the supplied US storefront only"
assert cfg["google_priority_market"]=="TW"
assert cfg["google_search_allocation"]["TW"]>cfg["google_search_allocation"]["US"]
assert all("gl=TW" in x or "gl=US" in x for x in cfg["google_categories"])
assert "hl=zh_TW&gl=US" in collector.official_url("Google Play","com.looperse.td3kingdom","US")
assert builder.to_variant({"store":"Google Play","country":"JP","app_id":"com.test.other","name":"Other","source_url":"https://play.google.com/store/apps/details?id=com.test.other"}) is None
assert builder.to_variant({"store":"App Store","country":"JP","app_id":"112233445","name":"Other","source_url":"https://apps.apple.com/jp/app/id112233445"}) is not None

assert collector.appid("https://play.google.com/store/apps/details?id=com.looperse.td3kingdom&hl=zh_TW","Google Play")=="com.looperse.td3kingdom"
assert collector.appid("https://apps.apple.com/us/app/ungodly/id6740617332","App Store")=="6740617332"
assert collector.date_only("2026-11-11")=="2026-11-11"
assert collector.date_only("Nov 11, 2026")=="" # never infer an unstructured timestamp
f={"feed":{"entry":[{"im:name":{"label":"測試新遊戲"},
    "link":{"attributes":{"href":"https://apps.apple.com/tw/app/something/id112233445"}},
    "im:artist":{"label":"Studio Test"},
    "im:releaseDate":{"label":"2026-11-11T00:00:00Z"}}]}}
rows=collector.apple_feed(f,"TW","newapplications")
assert len(rows)==1 and rows[0]["app_id"]=="112233445"
assert rows[0]["date_scope"]=="Apple 商品發行日期，非國家首發保證"
def gp(name,pid,country,rd="",status="已上市",dev="Example"):
 return {"name":name,"platforms":["Google Play"],"country":country,"region":"台灣" if country=="TW" else "國際",
    "developer":dev,"status":status,"source_url":f"https://play.google.com/store/apps/details?id={pid}&gl={country}",
    "release_date":rd,"date_scope":"官方發行日期","first_seen_at":"2026-11-12T08:00:00+00:00"}
def ios(name,app,country,rd="",dev="Example",pre=False):
 return {"name":name,"platforms":["App Store"],"country":country,"developer":dev,
    "source_url":f"https://apps.apple.com/{country.lower()}/app/game/id{app}",
    "release_date":rd,"preorder":pre,"source_kind":"Apple Lookup",
    "first_seen_at":"2026-11-12T08:00:00+00:00"}
catalog={"items":[
 gp("UnGodly","com.azragames.ungodly","TW","2026-11-11",dev="Azra Games"),
 gp("UnGodly","com.azragames.ungodly","US","2026-11-11",dev="Azra Games"),
 ios("UnGodly","6740617332","US","2026-12-20",dev="Azra Games",pre=True),
 gp("Three Kingdoms Combo Defense 2","com.looperse.td3kingdom","TW","2025-06-01"),
 gp("寰宇卡尊 Online","com.jiys.mfqb","TW","2026-11-12"),
 gp("LV 9.9B","com.curiousdotlab.level99","TW","2026-11-13"),
 gp("同名遊戲","com.dev.one","TW","2026-11-12",dev="A Dev"),
 ios("同名遊戲","112233445","US","2026-11-11",dev="Different Dev")
]}
result,metrics=builder.build(catalog,{"items":[]},{"items":[]},cfg,dt.date(2026,11,14))
games=result["games"]
assert len(games)==6,[(x["id"],x["name"]) for x in games]
ungodly=next(x for x in games if x["id"]=="ungodly")
assert len(ungodly["variants"])==3,ungodly
assert set(x["platform"] for x in ungodly["variants"])=={"Android","iOS"}
assert any(x["status"]=="預購" for x in ungodly["variants"])
assert {"新上市","預約／預先註冊"}<=set(ungodly["categories"])
towers=next(x for x in games if x["id"]=="three-kingdoms-combo-defense-2")
assert "新上市" not in towers["categories"],towers
assert "三國組合塔防2" in towers["aliases"]
lv=next(x for x in games if x["id"]=="lv99b")
assert "等級99億" in lv["aliases"]
same_name=[x for x in games if x["name"]=="同名遊戲"]
assert len(same_name)==2,"Never merge equal titles with different developers"
assert all(v.get("date_scope") for v in ungodly["variants"] if v["date"])
print("PASS: four benchmark app IDs, TW/US & iOS status, language aliases, update-date safeguards, false-merge avoidance")
