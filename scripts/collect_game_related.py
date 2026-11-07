#!/usr/bin/env python3
"""For each newly listed game, look for recent code, guide and event source leads.

Searches are rotating, bounded, and historical: no source is labeled as a
redeemable code or dated event unless a separate extractor finds explicit facts.
"""
import datetime as dt
import email.utils
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOW = dt.datetime.now(dt.timezone.utc)
CONF = json.loads((ROOT / "config/content_sources.json").read_text(encoding="utf-8"))
LOOKBACK = int(CONF.get("lookback_days", 10))
LIMIT = 15
KINDS = {
    "codes": "(兌換碼 OR 禮包碼 OR 序號 OR redeem code)",
    "guides": "(攻略 OR 新手 OR 配隊 OR guide)",
    "events": "(活動 OR 聯動 OR 慶典 OR event)",
}
INVALID = re.compile(r"^(?:圖片|縮圖|螢幕截圖|檢視|新遊戲|圖示|icon|image)$", re.I)

def normalized(value):
    s = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[\W_]+", "", s)

def valid_name(name):
    t = str(name).strip("「」『』\" ")
    if len(t) < 3 or len(t) > 70 or INVALID.fullmatch(t): return False
    if re.search(r"(?:縮圖|螢幕截圖|圖示)圖片$", t): return False
    if t.count(",") >= 2: return False
    return True

def games_to_check(catalog, previous, limit=LIMIT):
    unique = {}
    for row in catalog:
        name = row.get("name", "").strip()
        if not valid_name(name): continue
        k = normalized(name)
        if k and k not in unique: unique[k] = name
    checked = previous.get("checked_games", {})
    # Unchecked games first; previously checked games rotate oldest-to-newest.
    keys = sorted(unique, key=lambda k:(checked.get(k, ""), k))
    return [(k, unique[k]) for k in keys[:limit]]

def rss_items(game, kind, getter=None):
    q = '"' + game.replace('"', "") + '" ' + KINDS[kind]
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": q + " when:10d", "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"})
    if getter is None:
        def getter(target):
            req = urllib.request.Request(target, headers={"User-Agent": "GameIntelSourceDiscovery/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status != 200: raise RuntimeError("HTTP " + str(resp.status))
                return resp.read(1_400_000)
    root = ET.fromstring(getter(url))
    cutoff = NOW - dt.timedelta(days=LOOKBACK)
    results = []
    for e in root.findall("./channel/item")[:20]:
        title = (e.findtext("title") or "").strip()
        link = (e.findtext("link") or "").strip()
        if not title or not link or not normalized(game) in normalized(title):continue
        p = urllib.parse.urlparse(link)
        if p.scheme != "https" or not p.netloc: continue
        try:
            published = email.utils.parsedate_to_datetime(e.findtext("pubDate") or "")
            if published.tzinfo is None: published = published.replace(tzinfo=dt.timezone.utc)
            if published < cutoff: continue
            published_at = published.isoformat()
        except (ValueError, TypeError): continue
        src = e.find("source")
        results.append({
            "game": game, "kind": kind, "title": title[:250],
            "source_url": link, "published_at": published_at,
            "publisher": src.text if src is not None and src.text else "",
            "status": "source_lead_only"
        })
        if len(results)>=6:break
    return results

def add_leads(existing, found):
    output={}
    for kind in KINDS:
        combined={}
        for row in (existing.get(kind, []) + found.get(kind, [])):
            if not isinstance(row, dict):continue
            link=row.get("source_url") or row.get("url")
            if not link:continue
            key=(normalized(row.get("game","")),link)
            combined[key]=row
        output[kind]=sorted(combined.values(),key=lambda x:x.get("published_at",""),reverse=True)[:400]
    return output

def run(catalog_path=None, leads_path=None, status_path=None, getter=None):
    catalog_path = catalog_path or DATA / "game_catalog.json"
    leads_path = leads_path or DATA / "source_leads.json"
    status_path = status_path or DATA / "game_related_status.json"
    catalog=json.loads(catalog_path.read_text(encoding="utf-8")).get("items",[])
    existing=json.loads(leads_path.read_text(encoding="utf-8")) if leads_path.exists() else {"items":{}}
    old=json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    checked=dict(old.get("checked_games",{}))
    selected=games_to_check(catalog, old)
    found={kind:[] for kind in KINDS}
    failures=[]; successes=0; counts={}
    for key,game in selected:
        per_game={}
        for kind in KINDS:
            try:
                rows=rss_items(game,kind,getter)
                found[kind].extend(rows);successes+=1
                per_game[kind]=len(rows)
            except Exception as exc:
                failures.append({"game":game,"kind":kind,"error":str(exc)[:180]})
                per_game[kind]=None
        if any(v is not None for v in per_game.values()):
            checked[key]=NOW.isoformat(timespec="seconds")
        counts[game]=per_game
    merged=add_leads(existing.get("items",{}),found)
    if merged!=existing.get("items",{}):
        existing["items"]=merged
        existing["updated_at"]=NOW.isoformat(timespec="seconds")
        existing["note"]="依商店遊戲名稱自動搜尋；原文線索不代表代碼可使用、攻略全文或活動日期已核實。"
        leads_path.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    status={
        "checked_at":NOW.isoformat(timespec="seconds"),
        "games_this_run":len(selected),
        "searches_succeeded":successes,
        "searches_failed":len(failures),
        "found_this_run":{kind:len(rows) for kind,rows in found.items()},
        "total_leads":{kind:len(rows) for kind,rows in merged.items()},
        "per_game":counts,
        "checked_games":checked,
        "errors":failures[:50],
    }
    status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Game-related searches:", json.dumps({k:v for k,v in status.items() if k not in ("checked_games","errors","per_game")},ensure_ascii=False))
    return status

if __name__=="__main__":run()
