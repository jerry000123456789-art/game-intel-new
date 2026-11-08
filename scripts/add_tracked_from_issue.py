#!/usr/bin/env python3
"""Safely accept a watch-game issue from the repository owner only."""
import datetime as dt,json,re,sys,urllib.parse
from pathlib import Path
event=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
issue=event.get('issue',{})
if issue.get('user',{}).get('login')!='jerry000123456789-art':
    raise SystemExit('Only owner can add cloud tracking games')
title=(issue.get('title') or '').strip()
prefix='[追蹤遊戲] '
if not title.startswith(prefix):raise SystemExit('Not a tracking issue')
name=title[len(prefix):].strip()
if not 2<=len(name)<=65 or re.search(r'[<>\n\r\\]',name):
    raise SystemExit('Invalid game name')
body=str(issue.get('body') or '')
match=re.search(r'(?:來源|官方網址)\s*[:：]\s*(https://[^\s<>]+)',body)
url=match.group(1).strip() if match else ''
if url:
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username:
        raise SystemExit('Invalid URL')
p=Path('config/tracked_games.json')
data=json.loads(p.read_text(encoding='utf8'))
if any(g.get('name','').casefold()==name.casefold() for g in data.get('games',[])):
    print('Already tracked',name);raise SystemExit(0)
data.setdefault('games',[]).append({'name':name,'source_url':url,
  'added_at':dt.datetime.now(dt.timezone.utc).isoformat(),
  'source_issue':issue.get('html_url','')})
data['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Added tracked game',name)
