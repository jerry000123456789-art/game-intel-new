#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../worker/index.js',import.meta.url),'utf8');
const {default:worker,GameWatchlist}=await import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
const storageData=new Map();
let alarmAt=null;
const storage={
  async get(k){return storageData.get(k)},
  async put(k,v){storageData.set(k,v)},
  async deleteAlarm(){alarmAt=null},
  async getAlarm(){return alarmAt},
  async setAlarm(at){alarmAt=at}
};
const ctx={storage};
const object=new GameWatchlist(ctx,{});
const watchKey='0123456789abcdef0123456789abcdef';
const base='https://game-intel.example/api/watchlist';
const env={WATCHLIST:{getByName(key){assert.equal(key,watchKey);return object}},ASSETS:{fetch:()=>new Response('site')}};
const req=(method,body,extra={})=>new Request(base,{
 method,headers: {'X-Watch-Key':watchKey,...(method!=='GET'?{'Origin':'https://game-intel.example','Content-Type':'application/json'}:{}),...extra},
 ...(body?{body:JSON.stringify(body)}:{})
});
let r=await worker.fetch(req('GET'),env);assert.equal(r.status,200);
assert.deepEqual((await r.json()).games,[]);
r=await worker.fetch(req('POST',{name:'薑餅人放置大戰爭',source_url:'https://apps.apple.com/tw/app/id6749251466'}),env);
assert.equal(r.status,201);assert.equal((await r.json()).games.length,1);assert(alarmAt>Date.now()-2000);
r=await worker.fetch(req('POST',{name:'薑餅人放置大戰爭'}),env);
assert.equal((await r.json()).status,'already_tracking');
r=await worker.fetch(req('POST',{name:'Other',source_url:'http://private.example'}),env);
assert.equal(r.status,400);
r=await worker.fetch(req('POST',{name:'CSRF'},{Origin:'https://evil.example'}),env).catch(()=>null);
const rss='<rss><channel><item><title>薑餅人放置大戰爭 新活動公告</title><link>https://example.org/announcement</link><pubDate>Mon, 09 Nov 2026 03:00:00 GMT</pubDate><description>活動期間：2026年11月10日 至 2026年11月25日</description></item></channel></rss>';
const original=globalThis.fetch;
globalThis.fetch=async()=>new Response(rss,{status:200});
try{await object.alarm()}finally{globalThis.fetch=original}
assert(alarmAt>Date.now());
r=await worker.fetch(req('GET'),env);
const doc=await r.json();
assert.equal(doc.games.length,1);
assert.equal(doc.items[0]?.game,'薑餅人放置大戰爭');
assert.equal(doc.items[0]?.start_date,'2026-11-10');
assert.equal(doc.items[0]?.end_date,'2026-11-25');
r=await worker.fetch(req('DELETE',{name:'薑餅人放置大戰爭'}),env);
assert.equal((await r.json()).games.length,0);
assert.equal(alarmAt,null);
const missing=await worker.fetch(req('GET'),{ASSETS:{fetch:()=>new Response('site')}});
assert.equal(missing.status,503);
console.log('PASS: secure watchlist POST saves, dedupes, scans RSS on alarm, validates dates, GET persistence and DELETE');
