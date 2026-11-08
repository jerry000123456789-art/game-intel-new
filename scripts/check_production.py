#!/usr/bin/env python3
"""Verify the deployed production site from GitHub's external runner."""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
BASE="https://game-intel-new.jerry000123456789.workers.dev"

def get(path,timeout=17):
    req=Request(BASE+path,headers={"User-Agent":"GameIntel-Production-Smoke/1.0","Accept":"*/*"})
    with urlopen(req,timeout=timeout) as r:
        return r.status,r.headers.get("Content-Type",""),r.read(2500000)

def check():
    problems=[]
    try:
        status,ctype,data=get("/?smoketest=site")
        html=data.decode("utf-8","replace")
        marks=("全球遊戲情報中心","僅顯示有實際兌換碼的遊戲","查最近 10 天活動公告","查最近 10 天攻略")
        missing=[x for x in marks if x not in html]
        print("WEBSITE: HTTP",status,"bytes",len(data),"matching new markers",len(marks)-len(missing))
        if status!=200 or "html" not in ctype or missing:problems.append("Website not latest, missing "+str(missing))
    except Exception as exc:problems.append("Website fetch: "+str(exc))
    try:
        status,ctype,data=get("/data/coverage_status.json?smoketest=data")
        server=json.loads(data)
        local=json.loads((ROOT/"data/coverage_status.json").read_text(encoding="utf-8"))
        a=server.get("sections",{}).get("game_catalog",{}).get("count",0)
        b=local.get("sections",{}).get("game_catalog",{}).get("count",0)
        print("DATA: GitHub count",b,"Cloudflare count",a,"server checked",server.get("checked_at"))
        if status!=200 or "json" not in ctype or a<b:problems.append("Cloudflare data outdated "+str(a)+" < "+str(b))
    except Exception as exc:problems.append("JSON asset fetch: "+str(exc))
    source_modes=[]
    for kind in ("events","guides"):
        path="/api/lookup?"+urlencode({"kind":kind,"game":"原神"})
        try:
            status,ctype,data=get(path,timeout=19)
            payload=json.loads(data)
            rows=payload.get("entries")
            mode=payload.get("source_mode","unknown")
            source_modes.append(mode)
            print("LOOKUP:",kind,"HTTP",status,"status",payload.get("status"),"mode",mode,"entries",len(rows) if isinstance(rows,list) else "?")
            if status!=200 or payload.get("status")!="ok" or not isinstance(rows,list) or mode not in ("live_rss","scheduled_cache"):
                problems.append("Lookup "+kind+" returned invalid JSON or source mode")
            if mode=="scheduled_cache" and not payload.get("updated_at"):
                problems.append("Lookup "+kind+" cache missing timestamp")
        except HTTPError as exc:
            problems.append("Lookup "+kind+" HTTP "+str(exc.code)+" "+exc.read(200).decode("utf-8","replace"))
        except Exception as exc:problems.append("Lookup "+kind+" failed: "+str(exc))
    if problems:
        print("PRODUCTION CHECK FAILED:")
        for p in problems:print(" -",p)
        return False
    print("PRODUCTION CHECK PASSED: latest UI, current JSON and functioning search API; sources:", ', '.join(source_modes))
    return True

if __name__=="__main__":
    tries=int(os.getenv("ATTEMPTS","3"))
    for attempt in range(tries):
        print("CHECK",attempt+1,"of",tries,flush=True)
        if check():break
        if attempt+1==tries:raise SystemExit(1)
        time.sleep(14)
