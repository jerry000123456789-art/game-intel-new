#!/usr/bin/env python3
"""External smoke test: deployed storefront country/OS data and historical search UI."""
import json
import os
import time
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE="https://game-intel-new.jerry000123456789.workers.dev"

def get(path):
    request=Request(BASE+path,headers={"User-Agent":"GameIntel-Production-Check/2.0","Accept":"*/*"})
    with urlopen(request,timeout=18) as response:
        return response.status,response.headers.get("Content-Type",""),response.read(6000000)

def check():
    problems=[]
    try:
        status,ctype,data=get("/?release_check=1")
        html=data.decode("utf-8","replace")
        marks=["全球遊戲情報中心","國際全部國家","平台 × 國家 上市日期",
               "最近 30 天攻略原文","最近 30 天活動公告","僅顯示有實際兌換碼的遊戲"]
        missing=[x for x in marks if x not in html]
        print("FRONTEND:",status,"bytes",len(data),"missing",missing,flush=True)
        if status!=200 or "html" not in ctype or missing:problems.append("Production frontend not updated")
    except Exception as e:problems.append("HTML unavailable: "+str(e))
    try:
        status,ctype,data=get("/data/coverage_status.json?release_check=1")
        server=json.loads(data);local=json.loads((ROOT/"data/coverage_status.json").read_text(encoding="utf8"))
        live_count=server.get("sections",{}).get("game_catalog",{}).get("count",0)
        git_count=local.get("sections",{}).get("game_catalog",{}).get("count",0)
        print("GAME CATALOG: GitHub",git_count,"Cloudflare",live_count)
        if status!=200 or live_count<git_count:problems.append("Catalog data not deployed")
    except Exception as e:problems.append("Catalog JSON unavailable: "+str(e))
    try:
        status,ctype,data=get("/data/release_matrix.json?release_check=1")
        server=json.loads(data)
        local=json.loads((ROOT/"data/release_matrix.json").read_text(encoding="utf8"))
        live=server.get("items",[]);repo=local.get("items",[])
        p={x.get("platform") for x in live};countries={x.get("country") for x in live if x.get("platform")=="iOS"}
        print("RELEASE MATRIX:",len(live),"deployed rows;",len(repo),"GitHub rows; platforms",p,"iOS countries",countries,flush=True)
        if status!=200 or not {"Android","iOS"}.issubset(p) or not {"TW","US","JP","KR"}.issubset(countries) or len(live)<len(repo):
            problems.append("Cross-platform/country release matrix missing or stale")
    except Exception as e:problems.append("Release matrix unavailable: "+str(e))
    if problems:
        print("PRODUCTION CHECK FAILED:")
        for p in problems:print(" -",p)
        return False
    print("PRODUCTION CHECK PASSED: public site, historic filters, Android/iOS country matrix, latest GitHub data")
    return True

if __name__=="__main__":
    attempts=int(os.getenv("ATTEMPTS","3"))
    for i in range(attempts):
        print("CHECK",i+1,"of",attempts,flush=True)
        if check():break
        if i+1==attempts:raise SystemExit(1)
        time.sleep(20)
