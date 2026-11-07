#!/usr/bin/env python3
"""Discover payment/collaboration evidence on provider-owned websites by game name.

A news article on MyCard does NOT prove that MyCard can be used to pay for
the game. Results distinguish store/product listings from mere mentions.
"""
import datetime as dt
import json
from pathlib import Path
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collect_game_related import normalized, valid_name

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
NOW=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
PROVIDERS=[
    ("MyCard","app.mycard520.com.tw","儲值"),
    ("GASH","gashpoint.com.tw","儲值"),
    ("Razer Gold","gold.razer.com","game"),
    ("Codashop","codashop.com","top up"),
    ("UniPin","unipin.com","top up"),
    ("Midasbuy","midasbuy.com","top up"),
]
LIMIT_GAMES=8
MAX_RESULTS=4

def search_url(provider,domain,game,term):
    q=f'site:{domain} "{game.replace(chr(34),"")}" {term}'
    return "https://www.bing.com/search?" + urllib.parse.urlencode({"q":q,"format":"rss"})

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; GameIntelPaymentResearch/1.0)"})
    with urllib.request.urlopen(req,timeout=10) as resp:
        if resp.status!=200:raise RuntimeError("HTTP "+str(resp.status))
        return resp.read(1_300_000)

def discover(game,provider,domain,term,getter=fetch):
    xml=getter(search_url(provider,domain,game,term))
    root=ET.fromstring(xml)
    out=[]
    for row in root.findall(".//item"):
        title=(row.findtext("title") or "").strip()
        description=(row.findtext("description") or "").strip()
        url=(row.findtext("link") or "").strip()
        p=urllib.parse.urlparse(url)
        hostname=(p.hostname or "").lower()
        if p.scheme!="https" or not (hostname==domain or hostname.endswith("."+domain)):continue
        if normalized(game) not in normalized(title+" "+description):continue
        # Official provider *news* counts only as an association lead.
        is_news=bool(re.search(r"/(?:news[-/]|articles?/|blog/)",p.path,re.I))
        has_payment_text=bool(re.search(r"儲值|購買|扣點|充值|付費|top.?up|direct.?top.?up|purchase|gift.?card",title+" "+description,re.I))
        listing=bool(re.search(r"/(?:gold/catalog/|games?/|shop/|store/|product/|top.?up/|recharge/)",p.path,re.I))
        evidence="商品／儲值頁" if listing and has_payment_text and not is_news else "合作／相關報導"
        out.append({"game":game,"provider":provider,"source_url":url,"title":title[:200],
                    "evidence":evidence,"verification_status":"公開頁面線索，未經實際付款測試",
                    "first_seen_at":NOW})
        if len(out)>=MAX_RESULTS:break
    return out


# Primary evidence: directly read official payment provider game/product directories.
DIRECTORIES=[
    ("MyCard","https://www.mycard520.com/web/zh-tw/MicroPayment","官方線上購點／教學目錄（不代表遊戲內直接扣點）"),
    ("GASH","https://tw.gashpoint.com/games/list/game","官方合作遊戲目錄（可用渠道依商品頁）"),
    ("Razer Gold","https://gold.razer.com/tw/en/gold/catalog","遊戲商品目錄（非遊戲內直接付費證明）"),
    ("Codashop","https://www.codashop.com/zh-tw/","台灣官方儲值商品目錄（須核對地區）"),
    ("Midasbuy","https://www.midasbuy.com/midasbuy/us?lang=en","官方儲值商品目錄（海外地區可用性需核對）"),
]
ALIASES={
    "原神":["Genshin Impact"],
    "絕區零":["Zenless Zone Zero"],
    "鳴潮":["Wuthering Waves"],
    "勝利女神：妮姬":["GODDESS OF VICTORY: NIKKE","NIKKE"],
    "Garena® 三角洲行動":["Delta Force"],
}
class VisibleDirectoryHTML(__import__("html.parser",fromlist=["HTMLParser"]).HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.labels=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg") and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:
            val=" ".join(data.split()).strip()
            if val and len(val)<160:self.labels.append(val)
def official_directory_matches(html,game_names,provider,url,evidence):
    parser=VisibleDirectoryHTML()
    parser.feed(html)
    labels={normalized(label) for label in parser.labels}
    results=[]
    for name in game_names:
        if not valid_name(name):continue
        aliases=[name]+ALIASES.get(name,[])
        if not any(normalized(x) in labels for x in aliases):continue
        results.append({"game":name,"provider":provider,"source_url":url,
            "title":"官方目錄列出 "+name,"evidence":evidence,
            "verification_status":"公開目錄比對；未登入測試付款、地區及商品有效性",
            "first_seen_at":NOW})
    return results
def scan_official_directories(game_names,getter=fetch):
    found=[];errors=[];checked=0
    for provider,url,evidence in DIRECTORIES:
        try:
            data=getter(url)
            page=data.decode("utf-8","replace") if isinstance(data,bytes) else str(data)
            matches=official_directory_matches(page,game_names,provider,url,evidence)
            found.extend(matches);checked+=1
            print("Payment directory:",provider,"matches",len(matches))
        except Exception as e:
            errors.append({"provider":provider,"error":str(e)[:180],"url":url})
    return found,checked,errors

def run(catalog_file=None,output_file=None,status_file=None,getter=fetch):
    catalog_file=catalog_file or DATA/"game_catalog.json"
    output_file=output_file or DATA/"payment_sources.json"
    status_file=status_file or DATA/"payment_status.json"
    games=json.loads(catalog_file.read_text(encoding="utf-8")).get("items",[])
    existing=json.loads(output_file.read_text(encoding="utf-8")) if output_file.exists() else {"items":[]}
    old=json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}
    checked=dict(old.get("checked_games",{}))
    available={normalized(x.get("name","")):(x.get("name",""),x.get("first_seen_at","")) for x in games if valid_name(x.get("name",""))}
    def priority(k):
        if k in checked:return (1,checked[k],k)
        try:ts=dt.datetime.fromisoformat(available[k][1].replace("Z","+00:00")).timestamp()
        except (ValueError,AttributeError):ts=0
        return (0,-ts,k)
    picks=sorted(available,key=priority)[:LIMIT_GAMES]
    combined={(normalized(x.get("game","")),x.get("provider",""),x.get("source_url","")):x
              for x in existing.get("items",[]) if x.get("source_url")}
    errors=[];ok=0;found=0
    directory_rows,directory_ok,directory_errors=scan_official_directories([v[0] for v in available.values()],getter)
    ok+=directory_ok
    errors.extend(directory_errors)
    for row in directory_rows:
        k=(normalized(row["game"]),row["provider"],row["source_url"])
        if k not in combined:combined[k]=row;found+=1
    for key in picks:
        succeeded=False
        for provider,domain,term in PROVIDERS:
            try:
                rows=discover(available[key][0],provider,domain,term,getter)
                ok+=1;succeeded=True
                for r in rows:
                    k=(normalized(r["game"]),r["provider"],r["source_url"])
                    if k not in combined:combined[k]=r;found+=1
            except Exception as e:
                errors.append({"game":available[key][0],"provider":provider,"error":str(e)[:150]})
        if succeeded:checked[key]=NOW
    rows=sorted(combined.values(),key=lambda x:x.get("first_seen_at",""),reverse=True)[:400]
    if rows!=existing.get("items",[]) or not output_file.exists():
        output_file.write_text(json.dumps({"updated_at":NOW,"items":rows,"note":"官方商店與合作來源線索；不能由新聞提及推斷可以直接付款。"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state={"updated_at":NOW,"games_this_run":len(picks),"searches_succeeded":ok,
           "searches_failed":len(errors),"new_evidence":found,"total_evidence":len(rows),
           "directories_succeeded":directory_ok,"directories_failed":len(directory_errors),
           "checked_games":checked,"errors":errors[:45]}
    status_file.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Payment provider lookup:",json.dumps({k:v for k,v in state.items() if k not in ("checked_games","errors")},ensure_ascii=False))
    return state

if __name__=="__main__":run()
