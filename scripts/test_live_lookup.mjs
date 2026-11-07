#!/usr/bin/env node
// Offline test of the exact Worker code used by Cloudflare; no external requests.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const code=await fs.readFile(new URL('../worker/index.js',import.meta.url),'utf8');
const {default:worker,parseRSS,decoded}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const date=new Date().toUTCString();
const makeRSS=(label,word)=>'<?xml version="1.0"?><rss><channel><item>'+
  '<title>'+label+' 公告'+word+'</title><link>https://gnn.gamer.com.tw/detail.php?sn=999900</link>'+
  '<pubDate>'+date+'</pubDate><source url="https://gnn.gamer.com.tw">巴哈姆特</source></item>'+
  '<item><title>無關的其他遊戲'+word+'</title><link>https://example.com/other</link>'+
  '<pubDate>'+date+'</pubDate></item></channel></rss>';
assert.equal(decoded('原神&amp;星穹'), '原神&星穹');
assert.equal(parseRSS(makeRSS('原神','活動'), '原神','events').length,1);
assert.equal(parseRSS(makeRSS('原神','活動'), '原神','guides').length,0);
const originalFetch=globalThis.fetch;
globalThis.fetch=async ()=>new Response(makeRSS('原神','活動時間資訊'),{status:200,headers:{'Content-Type':'application/rss+xml'}});
try {
  let res=await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%8E%9F%E7%A5%9E&kind=events'),{});
  assert.equal(res.status,200);
  let json=await res.json();
  assert.equal(json.status,'ok');
  assert.equal(json.entries.length,1);
  assert.match(json.entries[0].title,/活動/);
  assert.equal(json.entries[0].start_at,undefined);
  assert.equal((await worker.fetch(new Request('https://example.com/api/lookup?game=A&kind=events'),{})).status,400);
  assert.equal((await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%8E%9F%E7%A5%9E&kind=invalid'),{})).status,400);
  globalThis.fetch=async()=>new Response('temporarily unavailable',{status:503});
  let unavailable=await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%8E%9F%E7%A5%9E&kind=events'),{});
  assert.equal(unavailable.status,503);
  assert.equal((await unavailable.json()).status,'unavailable');
  console.log('PASS: live per-game lookup, event/guide classification, no inferred event start date, validation and network fallback');
} finally {
  globalThis.fetch=originalFetch;
}
