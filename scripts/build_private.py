#!/usr/bin/env python3
"""Publish only intended site files, never scripts/config/secrets to static assets."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'public'
if out.exists(): shutil.rmtree(out)
(out/'data').mkdir(parents=True)
shutil.copy2(ROOT/'index.html',out/'index.html')
for src in (ROOT/'data').glob('*.json'):
    shutil.copy2(src,out/'data'/src.name)
(out/'robots.txt').write_text('User-agent: *\nDisallow: /\n',encoding='utf-8')
print('Built public site assets:',len(list(out.rglob('*'))),'files')
