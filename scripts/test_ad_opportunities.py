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
assert m.safe_taptap("https://www.taptap.cn/moment/123")
assert not m.safe_taptap("https://evil.example/moment/123")
assert not m.safe_taptap("http://www.taptap.cn/moment/123")
html="<html><body><h1>《測試好遊戲》限時累充福利活動</h1><p>活動時間：2026年11月11日10:00 - 2026年11月25日23:59</p><p>充值達指定檔位領獎</p></body></html>"
url="https://www.taptap.cn/moment/123456"
lead=m.candidate_from_taptap(url,"《測試好遊戲》限時累充福利活動",html,"2026-11-11")
assert lead and lead["game"]=="測試好遊戲",lead
assert lead["start_date"]=="2026-11-11" and lead["end_date"]=="2026-11-25",lead
assert m.candidate_from_taptap(url,"《測試好遊戲》活動","<html><body><p>活動時間 11月11日至11月25日</p></body></html>","2026-11-11") is None
cn=m.evaluate(lead,cfg)
assert cn["market_label"]=="中國站" and "待核實" in cn["status"]
tw=m.evaluate({**lead,"market":"TW"},cfg)
assert tw["status"].startswith("優先評估"),tw
assert m.evaluate({**lead,"game":"原神"},cfg) is None
rss='<?xml version="1.0"?><rss><channel><item><title>《測試好遊戲》限時累充福利活動</title><link>'+url+'</link></item></channel></rss>'
def getter(target):
    return html if target==url else rss
with patch.object(m,"TODAY",dt.date(2026,11,11)):
    result,health=m.collect(config={**cfg,"reference_events":[]},previous={"items":[]},getter=getter)
assert health["queries_attempted"]==2*len(cfg["taptap_discovery_queries"])
assert health["taptap_dated_items_parsed"]==1,health
assert any(x["game"]=="測試好遊戲" and x["market"]=="CN" for x in result["items"])
assert not any(m.exclude(x["game"],cfg) for x in result["items"])
assert all(x["status"]!="可直接投放" for x in result["items"])
print("PASS: precise TapTap date discovery, miHoYo exclusions, China-region advertising gate and no inferred release periods")
