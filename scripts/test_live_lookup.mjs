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
  const stamp=new Date().toISOString(),url='https://gnn.gamer.com.tw/detail.php?sn=999900';
  const assets={
    fetch:async request=>{
      const path=new URL(request.url).pathname;
      const records={
        '/data/source_leads.json':{updated_at:stamp,items:{
          events:[{title:'原神 新版本活動即將登場',source_url:url,published_at:stamp,publisher:'巴哈姆特'}],
          guides:[{title:'原神 新手配隊攻略',source_url:url,published_at:stamp,publisher:'巴哈姆特'}]
        }},
        '/data/latest.json':{updated_at:stamp,items:[]},
        '/data/channel_history.json':{updated_at:stamp,items:[]}
      };
      return path in records?new Response(JSON.stringify(records[path]),{status:200}):new Response('missing',{status:404});
    }
  };
  let cached=await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%8E%9F%E7%A5%9E&kind=events'),{ASSETS:assets});
  assert.equal(cached.status,200);
  let snapshot=await cached.json();
  assert.equal(snapshot.status,'ok');
  assert.equal(snapshot.source_mode,'scheduled_cache');
  assert.equal(snapshot.entries.length,1);
  assert.equal(snapshot.entries[0].start_at,undefined);
  let cachedGuide=await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%8E%9F%E7%A5%9E&kind=guides'),{ASSETS:assets});
  assert.equal(cachedGuide.status,200);
  assert.equal((await cachedGuide.json()).entries.length,1);
  let unknown=await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%B9%BB%E6%83%B3%E9%81%8A%E6%88%B2&kind=events'),{ASSETS:assets});
  assert.equal(unknown.status,200);
  assert.equal((await unknown.json()).entries.length,0);
  let unavailable=await worker.fetch(new Request('https://example.com/api/lookup?game=%E5%8E%9F%E7%A5%9E&kind=events'),{});
  assert.equal(unavailable.status,503);
  assert.equal((await unavailable.json()).status,'unavailable');
  console.log('PASS: Worker lookup online, scheduled-cache fallback, empty matches and missing-cache errors');
} finally {
  globalThis.fetch=originalFetch;
}
