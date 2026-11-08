#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const a=html.indexOf('function storeCountry(x)'),
      b=html.indexOf('const STORE_SOURCES',a);
assert(a>=0&&b>a,'Missing country/storefront helpers');
const db={games:[
 {name:'測試遊戲',region:'台灣',country:'TW',platforms:['Google Play'],source_url:'https://play.google.com/store/apps/details?id=com.example.game&gl=TW',
  store_links:[{url:'https://play.google.com/store/apps/details?id=com.example.game&gl=TW'}],first_seen_at:'2026-11-08T00:00:00Z'},
 {name:'測試遊戲',region:'台灣',country:'TW',platforms:['App Store'],source_url:'https://apps.apple.com/tw/app/id123456789',
  store_links:[{url:'https://apps.apple.com/tw/app/id123456789'}],first_seen_at:'2026-11-08T01:00:00Z'},
 {name:'測試遊戲',region:'國際',country:'US',platforms:['App Store'],source_url:'https://apps.apple.com/us/app/id123456789',
  store_links:[{url:'https://apps.apple.com/us/app/id123456789'}],first_seen_at:'2026-11-08T02:00:00Z'}
],releaseMatrix:[
 {platform:'Android',app_id:'com.example.game',country:'TW',country_name:'台灣',availability:'商店目錄已收錄',source_url:'https://play.google.com/store/apps/details?id=com.example.game&gl=TW'},
 {platform:'iOS',app_id:'123456789',country:'TW',country_name:'台灣',availability:'商店有收錄',store_release_date:'2026-10-31',version_release_date:'2026-11-07',source_url:'https://apps.apple.com/tw/app/id123456789'},
 {platform:'iOS',app_id:'123456789',country:'US',country_name:'美國',availability:'商店有收錄',store_release_date:'2026-10-31',version_release_date:'2026-11-07',source_url:'https://apps.apple.com/us/app/id123456789'},
 {platform:'iOS',app_id:'123456789',country:'KR',country_name:'韓國',availability:'未確認',source_url:'https://apps.apple.com/kr/app/id123456789'}
]};
const helpers=new Function('db','gameKey','safe','link',html.slice(a,b)+
  'return {storeCountry,normalizeGame,uniqueGames,gameAppIds,releaseFor,releaseDateRows};')(
  db,x=>String(x||'').toLowerCase().replace(/[^\p{L}\p{N}]/gu,''),
  x=>String(x??''),(url,title)=>'<a href="'+url+'">'+title+'</a>');
assert.equal(helpers.storeCountry({source_url:'https://apps.apple.com/jp/app/thing/id2'}),'JP');
assert.equal(helpers.storeCountry({source_url:'https://play.google.com/store/apps/details?id=x&gl=US'}),'US');
const games=helpers.uniqueGames();
assert.equal(games.length,1);
const game=games[0];
assert(game.regions.includes('台灣')&&game.regions.includes('國際'));
assert(game.countries.includes('US')&&game.countries.includes('TW'));
assert.equal(helpers.releaseFor(game).length,4);
let release=helpers.releaseDateRows(game);
assert(release.includes('Android')&&release.includes('iOS'));
assert(release.includes('美國')&&release.includes('韓國'));
assert(release.includes('2026-10-31'));
assert(release.includes('尚未核實'));
assert(release.includes('目前版本更新'));
assert(html.includes('id="gameCountry"'));
assert(html.includes('最近 30 天攻略原文'));
assert(html.includes('最近 30 天活動公告'));
assert(!html.includes('id="guideLookupBtn"'));
assert(!html.includes('id="eventLookupBtn"'));
console.log('PASS: merged TW/international game, per-country Android/iOS release dates, 30-day stored searches and no live lookup controls');
