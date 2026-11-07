/** Public game intelligence site with read-only, on-demand game news lookup.
 * No login. Requests only fetch a fixed Google News RSS host, never user URLs.
 */
const KEYWORDS={
  events:/活動|活動時間|活動期間|聯動|改版|慶典|限時|賽季|更新|週年|周年|開服|event|collab|festival|season/i,
  guides:/攻略|教學|新手|配隊|培養|角色|裝備|陣容|指南|guide|build|tips|walkthrough/i,
};
function decoded(s){
  return String(s||'').replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g,'$1')
    .replace(/&#x([0-9a-f]+);/gi,(_,n)=>String.fromCodePoint(parseInt(n,16)))
    .replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(parseInt(n,10)))
    .replace(/&(?:amp|lt|gt|quot|apos|nbsp);/g,m=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&apos;':"'",'&nbsp;':' '}[m.toLowerCase()]||m))
    .replace(/<[^>]*>/g,'').trim();
}
function tag(section,name){
  const match=section.match(new RegExp('<'+name+'(?:\\s[^>]*)?>([\\s\\S]*?)<\\/'+name+'>','i'));
  return match?decoded(match[1]):'';
}
function matchesGame(title,game){
  const t=title.normalize('NFKC').toLocaleLowerCase(),g=game.normalize('NFKC').toLocaleLowerCase();
  return t.includes(g);
}
function parseRSS(xml,game,kind,now=Date.now()){
  const found=[],seen=new Set();
  const cutoff=now-10*86400000;
  for(const match of xml.matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)){
    const body=match[1],title=tag(body,'title'),url=tag(body,'link');
    const date=new Date(tag(body,'pubDate'));
    if(!title||!matchesGame(title,game)||!KEYWORDS[kind].test(title))continue;
    if(!Number.isFinite(date.getTime())||date.getTime()<cutoff)continue;
    let source;
    try{source=new URL(url);if(source.protocol!=='https:')continue;}catch{continue;}
    if(seen.has(source.href))continue;
    seen.add(source.href);
    found.push({title:title.slice(0,280),url:source.href,published_at:date.toISOString(),
      publisher:tag(body,'source').slice(0,90),
      date_status:'來源刊登日期；活動起訖日期未經確認'});
    if(found.length>=25)break;
  }
  return found.sort((a,b)=>b.published_at.localeCompare(a.published_at));
}
function reply(obj,status=200){
  return new Response(JSON.stringify(obj),{status,headers:{
    'Content-Type':'application/json; charset=utf-8',
    'Cache-Control':'public, max-age=180',
    'Access-Control-Allow-Origin':'*',
    'X-Content-Type-Options':'nosniff',
  }});
}
async function lookup(request){
  const url=new URL(request.url);
  const game=(url.searchParams.get('game')||'').trim();
  const kind=url.searchParams.get('kind');
  if(!kind||!Object.hasOwn(KEYWORDS,kind))return reply({error:'僅支援活動或攻略查詢'},400);
  if(game.length<2||game.length>60||/[\u0000-\u001f<>]/.test(game))return reply({error:'請輸入 2–60 字的遊戲名稱'},400);
  const phrase='"'+game.replace(/["\\]/g,'').replace(/\s+/g,' ').trim()+'"';
  const q=phrase+' '+(kind==='events'?'(活動 OR 聯動 OR 改版 OR 限時 OR event)':'(攻略 OR 教學 OR 配隊 OR guide OR build)')+' when:10d';
  const rss=new URL('https://news.google.com/rss/search');
  for(const [key,value] of Object.entries({q,hl:'zh-TW',gl:'TW',ceid:'TW:zh-Hant'}))rss.searchParams.set(key,value);
  try{
    const response=await fetch(rss.toString(),{
      headers:{'User-Agent':'GameIntelLookup/1.0','Accept':'application/rss+xml,application/xml,text/xml'},
      signal:AbortSignal.timeout(9500),
    });
    if(!response.ok)throw new Error('新聞來源回應 HTTP '+response.status);
    const raw=await response.text();
    if(raw.length>1200000)throw new Error('來源資料超出大小限制');
    const entries=parseRSS(raw,game,kind);
    return reply({game,kind,checked_at:new Date().toISOString(),status:'ok',
      note:'這些是最近10天的公開原文線索；刊登日期不是活動開始日期。僅有已核實的活動起訖時間才應顯示為確定日期。',
      entries});
  }catch(e){
    return reply({game,kind,checked_at:new Date().toISOString(),status:'unavailable',
      error:'即時來源暫時無法取得，請查看網站已收錄的公告與原始網址。',entries:[]},503);
  }
}
export {parseRSS,decoded,matchesGame};
export default{
  async fetch(request,env){
    const url=new URL(request.url);
    if(url.pathname==='/api/lookup'){
      if(request.method!=='GET')return reply({error:'僅接受 GET'},405);
      return lookup(request);
    }
    const response=await env.ASSETS.fetch(request);
    const headers=new Headers(response.headers);
    headers.set('X-Content-Type-Options','nosniff');
    headers.set('Referrer-Policy','strict-origin-when-cross-origin');
    return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
  }
};
