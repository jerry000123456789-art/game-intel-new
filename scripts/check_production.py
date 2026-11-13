#!/usr/bin/env python3
"""External production validation of focused Cloudflare new-game radar."""
import json
import os
import time
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE="https://game-intel-new.jerry000123456789.workers.dev"

def fetch(path):
    req=Request(BASE+path,headers={"User-Agent":"GameRadarProductionVerifier/3.0"})
    with urlopen(req,timeout=22) as r:
        return r.status,r.headers.get("Content-Type",""),r.read(20_000_000)

def check():
    failed=[]
    try:
        status,ctype,data=fetch("/?radar_check=1")
        html=data.decode("utf-8","replace")
        required=["今日商機","新遊戲雷達","新上市","即將上市","預約／預先註冊",
                  "Google Play","App Store","id=\"game-search\"","radar.js","radar.css"]
        for item in required:
            if item not in html:failed.append("Page missing "+item)
        for obsolete in ("多平台文案工作台","攻略／創作者","我的活動追蹤"):
            if obsolete in html:failed.append("Obsolete UI still deployed: "+obsolete)
        if status!=200 or "text/html" not in ctype:failed.append("index HTTP/type mismatch")
        print("HOME:",status,"bytes",len(data),flush=True)
    except Exception as e:failed.append("HTML error "+str(e))
    for asset,marker in [("/radar.js","function render()"),("/radar.css","#EAEAEF")]:
        try:
            status,ctype,data=fetch(asset+"?v=radar-v2")
            if status!=200 or marker not in data.decode("utf-8","replace"):failed.append(asset+" not deployed")
            print("ASSET",asset,"HTTP",status,"bytes",len(data),flush=True)
        except Exception as e:failed.append(asset+" error "+str(e))
    try:
        status,ctype,data=fetch("/data/radar_catalog.json?radar_check=1")
        cloud=json.loads(data)
        local=json.loads((ROOT/"data/radar_catalog.json").read_text(encoding="utf8"))
        if not isinstance(cloud.get("games"),list) or not cloud["games"]:failed.append("Empty radar catalog")
        if cloud.get("updated_at")!=local.get("updated_at"):failed.append("Cloudflare radar data is stale")
        active=cloud.get("games") or []
        print("DATA:",len(active),"cards updated",cloud.get("updated_at"),flush=True)
        targets={"ungodly","three-kingdoms-combo-defense-2","huanyu-card-online","lv99b"}
        found={x.get("id") for x in active}
        missing=targets-found
        if missing:failed.append("Four owner verification games not all found: "+", ".join(sorted(missing)))
        for x in active:
            refs=[(v.get("platform"),v.get("id"),v.get("country")) for v in x.get("variants",[])]
            if len(refs)!=len(set(refs)):
                failed.append("Duplicate country/platform within game: "+x.get("name",""))
                break
        if status!=200:failed.append("Radar catalog HTTP error")
    except Exception as e:failed.append("Radar catalog not deployed: "+str(e))
    for name in ("radar_summary","radar_health"):
        try:
            status,ctype,data=fetch("/data/"+name+".json?radar_check=1")
            if status!=200 or not json.loads(data):failed.append("Missing "+name)
        except Exception as e:failed.append(name+" unavailable: "+str(e))
    if failed:
        print("RADAR PRODUCTION FAIL:")
        for f in failed:print(" - "+f)
        return False
    print("RADAR PRODUCTION PASS: focused UI, search assets, official-sourced game cards and four verification cases")
    return True

if __name__=="__main__":
    retries=int(os.getenv("ATTEMPTS","4"))
    for i in range(retries):
        print("CHECK",i+1,"/",retries,flush=True)
        if check():break
        if i+1==retries:raise SystemExit(1)
        time.sleep(12)
