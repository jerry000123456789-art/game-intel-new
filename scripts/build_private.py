#!/usr/bin/env python3
"""Publish only the focused mobile game radar and its public data."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'public'
if out.exists():shutil.rmtree(out)
(out/'data').mkdir(parents=True)
for name in ('index.html','radar.js','radar.css'):
    shutil.copy2(ROOT/name,out/name)
for name in ('radar_catalog','radar_summary','radar_health'):
    src=ROOT/'data'/(name+'.json')
    if not src.exists():raise SystemExit('Missing required public radar snapshot: '+str(src))
    shutil.copy2(src,out/'data'/src.name)
(out/'robots.txt').write_text('User-agent: *\nDisallow: /\n',encoding='utf8')
print('Focused radar build:',len(list(out.rglob('*'))),'assets')
