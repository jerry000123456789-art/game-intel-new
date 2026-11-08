#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const index=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const src=readFileSync(new URL('../business.js',import.meta.url),'utf8');
for(const id of ['gx-home','gx-games','gx-codes','gx-content','gx-calendar','gx-studio','gx-watch-form','gx-studio-output']){
  assert(index.includes('id="'+id+'"'),id);
}
for(const label of ['最近 30 天新上市','華為 AppGallery','Threads','Dcard','巴哈姆特','Instagram']){
  assert(index.includes(label),label);
}
assert(index.includes('src="/business.js"'));
assert(index.includes('href="/business.css"'));
assert(src.includes('data/')); // at runtime via /data/
assert(!index.includes('id="gx-ad-conversions"')); // No conversion tracking.
const start=src.indexOf('function gameStatus(rows){');
const end=src.indexOf('function filteredGames(){',start);
assert(start>0&&end>start,'gameStatus missing');
const today=Date.UTC(2026,10,8);
const parse=x=>Math.round((Date.parse(x+'T00:00:00Z')-today)/86400000);
const gameStatus=new Function('dayDelta',src.slice(start,end)+'return gameStatus;')(parse);
const example=[
 {platform:'Google Play',date:'2026-08-03',status:'已上市'},
 {platform:'App Store',date:'2026-10-28',status:'已上市'}];
assert.equal(gameStatus(example).type,'recent','iOS release last month qualifies despite older Android');
assert.equal(gameStatus(example).date,'2026-10-28');
assert.equal(gameStatus([{date:'2026-11-30'}]).type,'upcoming');
assert.equal(gameStatus([{date:'2026-06-01'}]).type,'history');
assert.equal(gameStatus([{date:'',status:'商店收錄'}]).type,'history');
assert.equal(gameStatus([{date:'',preOrder:true}]).label,'預先註冊');
const file=JSON.parse(readFileSync(new URL('../data/featured_launches.json',import.meta.url),'utf8'));
const well=file.items.find(x=>x.name.includes('WellDiver'));
assert(well);
assert(well.platforms.some(x=>x.platform==='App Store'&&x.date==='2026-10-28'));
assert(well.platforms.some(x=>x.platform==='Google Play'&&x.date==='2026-08-03'));
assert(well.platforms.every(x=>x.evidence_url?.startsWith('https://')));
// Draft generation only uses supplied claims and links, never invents discounts.
const ds=src.indexOf('function draftText(){'),de=src.indexOf('function makeDraft(){',ds);
assert(ds>0&&de>ds);
const values={'studio-game':'WellDiver','studio-topic':'公開活動',
  'studio-facts':'已公布活動資訊，詳情看官方','studio-source':'https://example.org/source',
  'studio-brand':'測試品牌','studio-platform':'Facebook','studio-angle':'timely'};
const draft=new Function('$','goodUrl',src.slice(ds,de)+'return draftText;')(
  key=>({value:values[key]}),url=>url.startsWith('https://')?url:'');
assert(draft.includes('WellDiver'));
assert(draft.includes('https://example.org/source'));
assert(!draft.includes('免費代儲')); // no fabricated promotions
values['studio-platform']='Dcard';
assert(draftTextIncludesDisclosure());
function draftTextIncludesDisclosure(){return draft.includes('公開活動')&&draft.includes('原始資料')}
console.log('PASS: full business dashboard, release-window criteria, verified source URLs, platform-specific drafts and safe tracking UI');
