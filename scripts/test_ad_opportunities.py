#!/usr/bin/env python3
"""Offline regression: correct source, date, region, exclusion and offer ranking."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("ad_radar",ROOT/"scripts/collect_ad_opportunities.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cfg=json.loads((ROOT/"config/ad_opportunity_sources.json").read_text(encoding="utf8"))
assert m.exclude("原神",cfg)
assert m.exclude("Genshin Impact",cfg)
assert m.exclude("崩壞：星穹鐵道",cfg)
assert m.exclude("Zenless Zone Zero",cfg)
assert not m.exclude("阴阳师",cfg)
# Google News matches cross-site announcements, but cannot assert event dates.
assert "news.google.com/rss/search" in m.google_news_url("神魔之塔 活動")
google_xml='<?xml version="1.0"?><rss><channel>'+
 '<item><title>《神魔之塔》推出限時儲值活動</title><link>https://news.google.com/rss/articles/example1</link><pubDate>Wed, 11 Nov 2026 06:00:00 GMT</pubDate><source>遊戲新聞</source></item>'+
 '<item><title>《原神》推出限時活動</title><link>https://news.google.com/rss/articles/example2</link><pubDate>Wed, 11 Nov 2026 06:00:00 GMT</pubDate><source>遊戲新聞</source></item>'+
 '<item><title>《神魔之塔》新活動</title><link>https://news.google.com/rss/articles/example3</link><pubDate>Wed, 11 Nov 2026 06:00:00 GMT</pubDate><source>遊戲新聞</source></item>'+
 '</channel></rss>'
with patch.object(m,"NOW",dt.datetime(2026,11,11,8,0,tzinfo=dt.timezone.utc)):
    leads,checked,ok,seen,errors=m.google_discover(cfg,lambda url:google_xml)
assert checked==cfg["google_general_queries_per_run"]+cfg["google_games_per_run"],checked
assert ok==checked and seen>0 and not errors,errors
assert any(x["game"]=="神魔之塔" and x["source_type"]=="Google 新聞搜尋" for x in leads),leads
assert not any(x["game"]=="原神" for x in leads),leads
assert all("start_date" not in x and "end_date" not in x and x["status"]=="source_lead_only" for x in leads)
assert m.safe_taptap("https://www.taptap.cn/moment/123")
assert not m.safe_taptap("https://evil.example/moment/123")
assert not m.safe_taptap("http://www.taptap.cn/moment/123")
html="<html><body><h1>《測試好遊戲》限時累充福利活動</h1><p>活動時間：2026年11月11日10:00 - 2026年11月25日23:59</p><p>充值達指定檔位領獎</p></body></html>"
url="https://www.taptap.cn/moment/123456"
lead=m.candidate_from_taptap(url,"《測試好遊戲》限時累充福利活動",html,"2026-11-11")
assert lead and lead["game"]=="測試好遊戲",lead
assert m.candidate_from_taptap(url,"限時福利活動",html,"2026-11-11","測試好遊戲")["game"]=="測試好遊戲"
assert lead["start_date"]=="2026-11-11" and lead["end_date"]=="2026-11-25",lead
assert m.candidate_from_taptap(url,"《測試好遊戲》活動","<html><body><p>活動時間 11月11日至11月25日</p></body></html>","2026-11-11") is None
cn=m.evaluate(lead,cfg)
assert cn["market_label"]=="中國站" and "待核實" in cn["status"] and cn["score"]<=48
tw=m.evaluate({**lead,"market":"TW"},cfg)
assert tw["status"].startswith("優先評估") and tw["score"]>cn["score"],tw
assert m.evaluate({**lead,"game":"原神"},cfg) is None
rss='<?xml version="1.0"?><rss><channel><item><title>《測試好遊戲》限時累充福利活動</title><link>'+url+'</link></item></channel></rss>'
def getter(target):
    return html if target==url else rss
with patch.object(m,"TODAY",dt.date(2026,11,11)):
    result,health=m.collect(config={**cfg,"reference_events":[]},previous={"items":[]},getter=getter)
assert health["google_queries_attempted"]==cfg["google_general_queries_per_run"]+cfg["google_games_per_run"]
assert health["taptap_queries_attempted"]==2*len(cfg["taptap_discovery_queries"])
assert health["queries_attempted"]==health["google_queries_attempted"]+health["taptap_queries_attempted"]
assert health["taptap_dated_items_parsed"]==1,health
assert any(x["game"]=="測試好遊戲" and x["market"]=="CN" for x in result["items"])
assert not any(m.exclude(x["game"],cfg) for x in result["items"])
assert all(x["status"]!="可直接投放" for x in result["items"])
print("PASS: broad Google News source leads without fabricated dates, conservative TapTap evidence, miHoYo exclusion and market gates")
