#!/usr/bin/env python3
"""Verify watchlist event matching and date extraction with no network."""
import importlib.util,datetime as dt
from pathlib import Path
p=Path(__file__).resolve().parent/'collect_tracked_events.py'
spec=importlib.util.spec_from_file_location('tracking',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.bounded_dates('原神 新活動','活動期間：2026年11月10日 至 2026年11月24日')==('2026-11-10','2026-11-24')
assert m.bounded_dates('原神 更新','來源刊登 2026年11月10日，更新於 2026年11月24日')==('','')
rss=b'<rss><channel><item><title>Original Game event</title><link>https://example.com/event</link><pubDate>Sun, 08 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>'
assert len(m.parse_feed(rss,'Original Game',dt.datetime(2026,11,9,tzinfo=dt.timezone.utc)))==1
assert not m.parse_feed(rss,'Another Game',dt.datetime(2026,11,9,tzinfo=dt.timezone.utc))
print('PASS: target-game event filtering and explicit date-range calendar safety')
