#!/usr/bin/env python3
"""Offline regression for real parser logic (not live network verification)."""
import datetime as dt, importlib.util, json, pathlib, tempfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
store=load('collect_store_pages')
facts=load('extract_facts')
# Pages contain actual app-link shapes, no fabricated release dates.
google='''<html><main><a href="/store/apps/details?id=com.example.game123" aria-label="測試遊戲甲"><img alt="測試遊戲甲"></a><a href="/store/apps/details?id=com.example.game456"><span>測試遊戲乙</span></a></main></html>'''
apple='''<html><main><a href="/tw/app/example-game/id123456789"><span>測試遊戲丙</span></a></main></html>'''
a=store.parse_store(google,'Google Play','台灣');b=store.parse_store(google,'Google Play','國際');c=store.parse_store(apple,'App Store','台灣')
assert len(a)==2,a
assert len(b)==2,b
assert len(c)==1,c
assert all(not x['release_date'] and x['status']=='商店收錄' for x in a+b+c)
assert all('gl=TW' in x['source_url'] for x in a)
assert all('gl=US' in x['source_url'] for x in b)
# Append followed by identical crawl must not create duplicate rows.
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);(p/'data').mkdir()
 (p/'data/game_catalog.json').write_text(json.dumps({'items':[]}),encoding='utf8')
 store.ROOT=p;store.OUTPUT=p/'data/game_catalog.json';store.HEALTH=p/'data/store_health.json'
 store.SOURCES=[('Google Play','台灣','https://example.test/tw'),('Google Play','國際','https://example.test/us'),('App Store','台灣','https://example.test/apple')]
 with patch.object(store,'fetch',side_effect=lambda u:apple if u.endswith('/apple') else google):
  store.run()
  one=json.loads(store.OUTPUT.read_text())['items']
  store.run()
  two=json.loads(store.OUTPUT.read_text())['items']
 assert len(one)==len(two)==5,(one,two)
 assert [x['id'] for x in one]==[x['id'] for x in two]
 assert [x['first_seen_at'] for x in one]==[x['first_seen_at'] for x in two]
# Only an explicit code with an attached source becomes a copyable code.
source='https://game.example/news'
code_list=facts.extract_codes('原神','活動公告 兌換碼：ABCDE12345。其他報導 兌換碼: ZYX987A2',source)
assert len(code_list)==2,code_list
assert all(x['verification_status']=='未實測' and x['source_url']==source for x in code_list)
assert not facts.extract_codes('原神','兌換碼 已公布，點擊進入遊戲查看詳情。',source)
assert not facts.extract_codes('','兌換碼：ABC123XYZ',source)
# Only an explicit bounded activity range may yield an event.
evs=facts.extract_event('原神','測試遊戲活動','活動時間：2026年11月03日 10:00 至 2026年11月12日 23:59。本活動依官方公告。',source)
assert len(evs)==1,evs
assert evs[0]['start_at'].startswith('2026-11-03T10:00')
assert not facts.extract_event('原神','遊戲活動','11月有新活動，時間尚未公布。',source)
assert not facts.extract_event('原神','遊戲活動','發布日期：2026/11/07，活動時間請看官網。',source)
print('PASS: TW/US Google Play + Apple parsing; 2nd pass append/dedupe; source-labeled untested codes; explicit event date ranges; no invented dates.')
