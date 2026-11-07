#!/usr/bin/env python3
"""Offline tests for new-game information and verified-provider source grouping."""
import datetime as dt
import json
import pathlib
import sys
import tempfile

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import collect_game_related as related
import collect_payment_methods as pay

date=dt.datetime.now(dt.timezone.utc)
pub=date.strftime("%a, %d %b %Y %H:%M:%S GMT")
rss=f'''<?xml version="1.0"?><rss><channel><item>
<title>測試新遊戲 公布兌換碼領取方式</title>
<link>https://gnn.gamer.com.tw/detail.php?sn=999</link>
<pubDate>{pub}</pubDate><source>巴哈姆特</source></item>
<item><title>無關遊戲 兌換碼</title><link>https://example.com/notmatch</link><pubDate>{pub}</pubDate></item>
</channel></rss>'''.encode()
items=related.rss_items("測試新遊戲","codes",lambda _:rss)
assert len(items)==1 and items[0]["game"]=="測試新遊戲"
assert not related.valid_name("螢幕截圖圖片")
assert not related.valid_name("檢視")
merged=related.add_leads({"codes":items},{"codes":items})
assert len(merged["codes"])==1
assert len(related.games_to_check([{"name":"測試新遊戲"},{"name":"檢視"}],{},limit=5))==1

provider_rss=b'''<?xml version="1.0"?><rss><channel>
<item><title>測試新遊戲 \xe5\x84\xb2\xe5\x80\xbc\xe5\x95\x86\xe5\x93\x81</title>
<link>https://app.mycard520.com.tw/games/testgame/</link>
<description>\xe6\xb8\xac\xe8\xa9\xa6\xe6\x96\xb0\xe9\x81\x8a\xe6\x88\xb2 \xe5\x84\xb2\xe5\x80\xbc</description></item>
<item><title>\xe6\xb8\xac\xe8\xa9\xa6\xe6\x96\xb0\xe9\x81\x8a\xe6\x88\xb2 \xe6\xb6\x88\xe6\x81\xaf</title>
<link>https://app.mycard520.com.tw/news-testgame</link>
<description>\xe6\xb8\xac\xe8\xa9\xa6\xe6\x96\xb0\xe9\x81\x8a\xe6\x88\xb2</description></item>
<item><title>\xe6\xb8\xac\xe8\xa9\xa6\xe6\x96\xb0\xe9\x81\x8a\xe6\x88\xb2 \xe5\x84\xb2\xe5\x80\xbc</title>
<link>https://evil.example/</link></item>
</channel></rss>'''
rows=pay.discover("測試新遊戲","MyCard","app.mycard520.com.tw","儲值",lambda _:provider_rss)
assert len(rows)==2,rows
assert rows[0]["evidence"]=="商品／儲值頁"
assert rows[1]["evidence"]=="合作／相關報導"
assert all("mycard520.com.tw" in x["source_url"] for x in rows)
with tempfile.TemporaryDirectory() as directory:
    p=pathlib.Path(directory)
    (p/"games.json").write_text(json.dumps({"items":[{"name":"測試新遊戲"}]},ensure_ascii=False))
    status=related.run(p/"games.json",p/"leads.json",p/"status.json",lambda _:rss)
    assert status["games_this_run"]==1 and status["searches_succeeded"]==3
    second=related.run(p/"games.json",p/"leads.json",p/"status.json",lambda _:rss)
    assert second["games_this_run"]==1 and len(json.loads((p/"leads.json").read_text())["items"]["codes"])==1
print("PASS: game sources rotate, merge without duplicates, provider ownership checked, news-only payment claims separated.")
