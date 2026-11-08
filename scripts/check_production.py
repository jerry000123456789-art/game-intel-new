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
        marks.extend(["id=\"businessApp\"","data-version=\"commercial-dashboard-v1\"","/business.js","/business.css","新增追蹤遊戲","多平台文案工作台"])
        missing=[x for x in marks if x not in html]
        print("FRONTEND:",status,"bytes",len(data),"missing",missing,flush=True)
        if status!=200 or "html" not in ctype or missing:problems.append("Production frontend not updated")
    except Exception as e:problems.append("HTML unavailable: "+str(e))
    for asset,mark in (("/business.js","function gameStatus(rows)"),("/business.css",".gx-app"),("/data/featured_launches.json","WellDiver"),("/data/tracked_events.json","items")):
        try:
            asset_status,asset_type,asset_data=get(asset+"?release_check=1")
            print("BUSINESS ASSET:",asset,"HTTP",asset_status,"bytes",len(asset_data),flush=True)
            if asset_status!=200 or mark not in asset_data.decode("utf-8","replace"):problems.append(asset+" not deployed")
        except Exception as e:problems.append(asset+" unavailable: "+str(e))
    try:
        test_key="97b4b4acbe0b4915bb6ee85e91269377"
        def watched(method="GET",record=None):
            payload=json.dumps(record,ensure_ascii=False).encode("utf-8") if record else None
            headers={"X-Watch-Key":test_key,"Accept":"application/json","User-Agent":"GameIntel-Production-Check/2.0"}
            if method!="GET":headers.update({"Origin":BASE,"Content-Type":"application/json"})
            req=Request(BASE+"/api/watchlist",data=payload,method=method,headers=headers)
            try:
                with urlopen(req,timeout=20) as response:return response.status,json.loads(response.read(200000))
            except Exception as exc:
                if hasattr(exc,"read"):
                    body=exc.read(1200).decode("utf8","replace")
                    print("WATCHLIST HTTP ERROR:",method,getattr(exc,"code",0),"BODY",body[:800],flush=True)
                raise
        # A live Worker route returns JSON 400 for an absent key; static assets do not.
        try:
            req=Request(BASE+"/api/watchlist",headers={"Accept":"application/json","User-Agent":"GameIntel-Production-Check/2.0"})
            with urlopen(req,timeout=10) as resp:
                print("WATCHLIST ROUTE PROBE:",resp.status,resp.read(300),flush=True)
        except Exception as probe_err:
            if hasattr(probe_err,"read"):
                print("WATCHLIST ROUTE PROBE:",getattr(probe_err,"code",0),probe_err.read(380).decode("utf8","replace"),flush=True)
            else:print("WATCHLIST ROUTE PROBE ERROR:",str(probe_err)[:200],flush=True)
        code,existing=watched()
        print("WATCHLIST API: GET",code,existing.get("source_mode"),flush=True)
        if code!=200 or existing.get("status")!="ok":problems.append("Cloud persistent watchlist unavailable")
        else:
            code,added=watched("POST",{"name":"自動驗收測試遊戲","source_url":"https://example.org/game"})
            print("WATCHLIST API: POST",code,added.get("status"),flush=True)
            if code not in (200,201) or added.get("status") not in ("saved","already_tracking"):
                problems.append("Cloud persistent save failed")
            code,saved=watched()
            if not any(x.get("name")=="自動驗收測試遊戲" for x in saved.get("games",[])):
                problems.append("Cloud persistent GET after save failed")
            # Confirm Cloudflare Durable Object actually wakes and performs its first scan.
            scanned=False
            for poll in range(8):
                if saved.get("last_scan_at") and saved.get("last_scan_at")!=existing.get("last_scan_at"):
                    scanned=True
                    break
                time.sleep(5)
                code,saved=watched()
            print("WATCHLIST ALARM:",("ran" if scanned else "not observed"),"checked",saved.get("last_scan_at"),"source errors",saved.get("errors"),"modes",saved.get("source_status"),flush=True)
            if not scanned:problems.append("Cloud watchlist background crawler alarm did not run")
            if scanned and saved.get("errors"):problems.append("Cloud watchlist has no working RSS or scheduled source fallback")
            if scanned and not saved.get("source_status"):problems.append("Cloud watchlist source monitoring was not recorded")
            code,deleted=watched("DELETE",{"name":"自動驗收測試遊戲"})
            if code!=200 or any(x.get("name")=="自動驗收測試遊戲" for x in deleted.get("games",[])):
                problems.append("Cloud persistent delete failed")
            else:print("WATCHLIST API: GET/POST/DELETE PASSED",flush=True)
    except Exception as e:problems.append("Watchlist backend not ready: "+str(e))
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
