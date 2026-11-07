#!/usr/bin/env python3
"""Derive clearly labeled release-news leads from existing RSS headlines.
No dates, regions, payment methods, or availability are inferred.
"""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
source = ROOT / 'data/latest.json'
if not source.exists():
    raise SystemExit('data/latest.json missing: run collect.py first')
raw = json.loads(source.read_text(encoding='utf-8'))
terms = re.compile(r'上市|推出|發售|開服|上線|公測|預約|事前登錄|測試|launch|release|pre.?register|early access', re.I)
exclude = re.compile(r'終止|取消上市|停止營運|下架|延後|延期|反應不佳|不佳|關服')
items = []
seen = set()
for x in raw.get('items', []):
    title = x.get('title', '')
    if not terms.search(title) or exclude.search(title):
        continue
    if x.get('category') != '新遊戲資訊':
        continue
    key = x.get('url') or title
    if key in seen:
        continue
    seen.add(key)
    # The RSS title is not sufficient to confirm a game identity or a release date.
    items.append({
        'name': title.rsplit(' - ', 1)[0][:180],
        'status': '上市消息',
        'region': '',
        'release_date': '',
        'platforms': [],
        'payment_methods': [],
        'store_links': [],
        'source_url': x.get('url', ''),
        'publisher': x.get('publisher', ''),
        'published_at': x.get('published_at', ''),
        'review_required': True,
    })
result = {'updated_at': raw.get('updated_at'), 'items': items[:120],
          'note': '新聞標題篩選出的上市消息，非已確認遊戲名單、上市日期或地區。'}
out = ROOT / 'data/launch_leads.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'launch_leads={len(result["items"])}')
