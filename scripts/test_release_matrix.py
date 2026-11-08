#!/usr/bin/env python3
"""Offline country and OS split tests: no invented release dates."""
import importlib.util,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_matrix",ROOT/"scripts/collect_release_matrix.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
apple="https://apps.apple.com/tw/app/test/id123456789"
google="https://play.google.com/store/apps/details?id=com.example.test&gl=TW"
catalog=[
 {"name":"測試遊戲","region":"台灣","platforms":["App Store"],"source_url":apple,"first_seen_at":"2026-11-08T10:00:00+00:00"},
 {"name":"測試遊戲","region":"台灣","platforms":["Google Play"],"source_url":google,"first_seen_at":"2026-11-08T11:00:00+00:00"},
]
info={"resultCount":1,"results":[{"trackId":123456789,"kind":"software","trackName":"測試遊戲",
    "releaseDate":"2026-10-31T00:00:00Z","currentVersionReleaseDate":"2026-11-07T03:00:00Z",
    "trackViewUrl":apple}]}
result,status=m.generate(catalog,fetch=lambda id,country:info if country in ("TW","US") else {"resultCount":0,"results":[]},limit=1,sleep=lambda x:None)
assert status["ios_countries_checked"]==len(m.COUNTRIES),status
rows=result["items"]
assert len([x for x in rows if x["platform"]=="Android"])==1,rows
android=[x for x in rows if x["platform"]=="Android"][0]
assert android["store_release_date"]=="" and android["country_launch_date"]==""
ios_tw=next(x for x in rows if x["platform"]=="iOS" and x["country"]=="TW")
ios_us=next(x for x in rows if x["platform"]=="iOS" and x["country"]=="US")
ios_jp=next(x for x in rows if x["platform"]=="iOS" and x["country"]=="JP")
assert ios_tw["store_release_date"]=="2026-10-31"
assert ios_tw["version_release_date"]=="2026-11-07"
assert ios_tw["country_launch_date"]=="",ios_tw
assert ios_us["country_launch_date"]==""
assert ios_jp["availability"]=="未確認"
old_tw=ios_tw["first_seen_in_country_at"]
two,second=m.generate(catalog,old=result,fetch=lambda id,country:info if country=="TW" else {"resultCount":0,"results":[]},limit=1,sleep=lambda x:None)
again=next(x for x in two["items"] if x["platform"]=="iOS" and x["country"]=="TW")
assert again["first_seen_in_country_at"]==old_tw
assert ios_us["availability"]=="商店有收錄"
assert next(x for x in two["items"] if x["platform"]=="iOS" and x["country"]=="US")["availability"]=="未確認"
assert m.apple_id_from_link(apple)=="123456789"
assert m.play_id_from_link(google)=="com.example.test"
from unittest.mock import patch
batch_calls=[]
def fake_batch(appids,country):
    batch_calls.append((tuple(appids),country))
    return info if country in ("TW","US") else {"resultCount":0,"results":[]}
with patch.object(m,"fetch_apple_batch",side_effect=fake_batch):
    product,status=m.generate(catalog,fetch=m.fetch_apple,limit=1,sleep=lambda value:None)
assert len(batch_calls)==len(m.COUNTRIES),batch_calls
assert status["ios_countries_checked"]==len(m.COUNTRIES)
assert next(x for x in product["items"] if x["platform"]=="iOS" and x["country"]=="US")["store_release_date"]=="2026-10-31"
print("PASS: per-country iOS lookup, Android separate, first seen preserved, version date != original launch")
