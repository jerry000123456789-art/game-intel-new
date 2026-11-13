import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {pathToFileURL} from "node:url";
import {resolve} from "node:path";
const source=readFileSync(new URL("../radar.js",import.meta.url),"utf8");
const url=pathToFileURL(resolve("radar.js"));
const m=await import(url.href);
const toy={
 id:"demo",name:"Three Kingdoms Combo Defense 2",other_name:"三國組合塔防2",
 aliases:["三國組合塔防2","Three Kingdoms Combo Defense 2"],developer:"Looperse",
 variants:[
  {id:"com.looperse.td3kingdom",store:"Google Play",platform:"Android",country:"TW",status:"已上市",date:"2025-06-01",source_url:"https://play.google.com/store/apps/details?id=com.looperse.td3kingdom"},
  {id:"com.looperse.td3kingdom",store:"Google Play",platform:"Android",country:"US",status:"已上市",date:"2025-06-01",source_url:"https://play.google.com/store/apps/details?id=com.looperse.td3kingdom"}
 ]
};
assert(m.searchMatches(toy,"三國組合塔防2"));
assert(m.searchMatches(toy,"THREE KINGDOMS Combo"));
assert(m.searchMatches(toy,"com.looperse.td3kingdom"));
assert(m.searchMatches(toy,"https://play.google.com/store/apps/details?id=com.looperse.td3kingdom&hl=zh_TW"));
assert(!m.searchMatches(toy,"寰宇卡尊"));
assert.equal(m.selectedVariants(toy,"all","TW").length,1);
assert.equal(m.selectedVariants(toy,"all","INT").length,1);
assert.equal(m.gameCategories(toy.variants,"2026-11-14").length,0);
const pre=[{platform:"iOS",store:"App Store",country:"TW",status:"預購",date:"2026-12-10"}];
assert(m.gameCategories(pre,"2026-11-14").includes("預約／預先註冊"));
let lines=m.platformLines(pre);
assert(lines.includes("iOS｜台灣"),lines);
assert(!lines.includes("Android"),lines);
assert(lines.includes("預約上架時間"),lines);
const recent=[{platform:"Android",store:"Google Play",country:"TW",status:"已上市",date:"2026-11-11"}];
assert(m.gameCategories(recent,"2026-11-14").includes("新上市"));
assert(m.platformLines(recent).includes("上架日期"));
assert(!m.platformLines(recent).includes("已確認可下載"));
const html=readFileSync(new URL("../index.html",import.meta.url),"utf8");
for(const text of ["新上市","即將上市","預約／預先註冊","Google Play","App Store","id=\"game-search\"","id=\"detail-dialog\""]){
 assert(html.includes(text),"Missing "+text);
}
for(const text of ["多平台文案工作台","我的活動追蹤","攻略／創作者"]){assert(!html.includes(text));}
assert(!source.includes("首次發布日期待確認"));
console.log("PASS: Chinese-only radar tabs, independent statuses, short dates, search aliases/IDs and detail view");
