#!/usr/bin/env python3
"""Offline integration test for RSS parsing, append and deduplication."""
import json, pathlib, subprocess, sys, tempfile, shutil
from unittest.mock import patch
from io import BytesIO
ROOT=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);(p/'scripts').mkdir();(p/'config').mkdir();(p/'data').mkdir()
 shutil.copy(ROOT/'scripts/collect_channels.py',p/'scripts/collect_channels.py')
 (p/'config/sources.json').write_text(json.dumps({'youtube_channels':['test'],'bahamut_feeds':['https://example.org/feed']}))
 youtube=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Video within recent 10 days</title><link href="https://www.youtube.com/watch?v=abc"/><published>2026-11-03T00:00:00Z</published></entry></feed>'''
 baha=b'''<rss><channel><item><title>Bahamut article within recent 10 days</title><link>https://gnn.gamer.com.tw/detail.php?sn=1</link><pubDate>Fri, 06 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'''
 class Resp:
  def __init__(self,body):self.body=BytesIO(body)
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self,*a):return self.body.read(*a)
 def fetch(req,timeout):return Resp(youtube if 'youtube.com' in req.full_url else baha)
 # Run script twice in-process with patched network and verify dedupe and history retention
 import runpy
 with patch('urllib.request.urlopen',fetch):
  for _ in range(2):runpy.run_path(str(p/'scripts/collect_channels.py'),run_name='__main__')
 rows=json.loads((p/'data/channel_history.json').read_text())['items']
 assert len(rows)==2,rows
 assert {r['origin'] for r in rows}=={'YouTube','巴哈姆特'}
 assert all(r['published_at'].startswith('2026-11') for r in rows)
 print('PASS: YouTube and Bahamut recent 10-day RSS fixtures parsed, history retained and deduped')
