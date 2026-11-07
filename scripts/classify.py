#!/usr/bin/env python3
"""Conservative structured leads from RSS metadata. Never asserts codes or event dates."""
import json, re, pathlib, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=ROOT/'data/latest.json'
if not source.exists():
    raise SystemExit('Missing data/latest.json; run collector first')
data=json.loads(source.read_text(encoding='utf-8'))
games=['原神','鳴潮','崩壞：星穹鐵道','崩壞 星穹鐵道','絕區零','明日方舟','楓之谷','勝利女神','妮姬','Last War','寒霜啟示錄','蔚藍檔案','無限暖暖','三國志','OVERGEARED']
dates=re.compile(r'(?<!\\d)(20\\d{2})[./年-](0?[1-9]|1[0-2])[./月-]([0-2]?\\d|3[01])(?:日)?')
records=[]
for item in data.get('items',[]):
    title=item.get('title','')
    matches=[g for g in games if g.casefold() in title.casefold()]
    found=[]
    for y,m,d in dates.findall(title):
        try: found.append(datetime.date(int(y),int(m),int(d)).isoformat())
        except ValueError: pass
    records.append({'id':item.get('id'), 'category':item.get('category'),
        'game_matches':matches, 'title':title, 'source_url':item.get('url',''),
        'publisher':item.get('publisher',''), 'published_at':item.get('published_at',''),
        'first_seen_at':item.get('first_seen_at',''), 'date_mentions':list(dict.fromkeys(found)),
        'review_required':True})
result={'updated_at':data.get('updated_at'),'note':'僅依標題比對遊戲與日期字樣；日期不代表活動起迄、上市日期；未擷取或驗證兌換碼。','items':records}
(ROOT/'data/classified.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')
print('classified='+str(len(records))+' game_matches='+str(sum(bool(x['game_matches']) for x in records)))
