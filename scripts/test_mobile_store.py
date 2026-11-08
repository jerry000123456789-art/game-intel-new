#!/usr/bin/env python3
"""Release statuses are backed by official fields, never update dates."""
import datetime as dt
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/(name+".py"))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module("enrich_mobile_store")
store=module("collect_store_pages")
past=(m.TODAY-dt.timedelta(days=10)).isoformat()
old=(m.TODAY-dt.timedelta(days=400)).isoformat()
future=(m.TODAY+dt.timedelta(days=12)).isoformat()
official_icon="https://play-lh.googleusercontent.com/TEST_GAME_ICON"
def ld(date):
    return ('<html><head><meta property="og:image" content="'+official_icon+'">'+
         '<script type="application/ld+json">'+
         '{"@type":"SoftwareApplication","datePublished":"'+date+'","image":"'+official_icon+'"}'+
         '</script></head><body><button>Install</button><span>Updated on</span><span>2026-11-08</span></body></html>')
facts=m.metadata_from_html(ld(past))
assert facts["store_release_date"]==past,facts
assert facts["cover_url"]==official_icon,facts
assert facts["officially_installed"] is True
assert facts["release_source_type"]=="Google Play 結構化發行日期"
assert m.status_for(past)=="新上市"
assert m.status_for(old)=="已上市"
assert m.status_for(future)=="即將上市"
assert m.status_for("",preorder=True)=="預先註冊"
assert m.status_for("",installable=False)=="商店收錄"
pre=m.metadata_from_html('<html><body><button>Pre-register</button><p>Updated on 2026-11-07</p></body></html>')
assert pre["preorder_confirmed"] and not pre["store_release_date"]
assert m.metadata_from_html('<html><p>Updated on</p><p>'+past+'</p></html>')["store_release_date"]==""
app_url="https://apps.apple.com/tw/app/test/id123456789"
play_url="https://play.google.com/store/apps/details?id=com.test.mobilegame&gl=TW"
catalog={"items":[
    {"name":"遊戲 A","platforms":["Google Play"],"region":"台灣","country":"TW","source_url":play_url,"cover_url":"","first_seen_at":"2026-11-08T00:00:00Z"},
    {"name":"遊戲 A","platforms":["App Store"],"region":"台灣","country":"TW","source_url":app_url,"cover_url":""},
    {"name":"PC game","platforms":["Steam"],"region":"國際","source_url":"https://store.steampowered.com/app/1/"}]}
matrix={"items":[{"platform":"iOS","app_id":"123456789","country":"TW","availability":"商店有收錄",
    "cover_url":"https://is1-ssl.mzstatic.com/image/thumb/test.png","store_release_date":old}]}
out,records,health=m.enrich(catalog,matrix,lookup=lambda x:facts,max_android=2)
assert len(out["items"])==2
a,b=out["items"]
assert a["cover_url"]==official_icon and a["status"]=="新上市",a
assert b["status"]=="已上市" and b["cover_url"].startswith("https://is1-ssl.mzstatic.com")
assert health["status_counts"].get("新上市")==1
assert health["status_counts"].get("已上市")==1
assert any(x["platform"]=="Android" and x.get("store_release_date")==past for x in records["items"])
tile='<a href="/store/apps/details?id=com.test.mobilegame"><img alt="遊戲 A" src="'+official_icon+'"></a>'
r=store.parse_store(tile,"Google Play","台灣","TW")
assert r[0]["cover_url"]==official_icon,r
assert not store.verified_cover("https://evil.example/fake.png","Google Play")
assert not m.official_art("https://evil.example/fake.png")
print("PASS: official covers, per-platform new/upcoming/preregister/old status, no Steam, no update-date-as-launch")
