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

async function getStored(env,request,filename){
  if(!env?.ASSETS)throw new Error('no ASSETS binding');
  const location=new URL('/data/'+filename+'.json',request.url);
  const response=await env.ASSETS.fetch(new Request(location.toString(),{method:'GET'}));
  if(!response.ok)throw new Error('stored '+filename+' HTTP '+response.status);
  return response.json();
}
function savedMatches(game,kind,sources,latest,channels,now=Date.now()){
  const period=now-10*86400000;
  const all=[...(sources?.items?.[kind]||[])];
  const category=kind==='events'?'活動行事曆':'遊戲攻略';
  for(const record of [...(latest?.items||[]),...(channels?.items||[])]){
    if(record.category===category || KEYWORDS[kind].test(record.title||''))all.push(record);
  }
  const seen=new Set(),result=[];
  for(const record of all){
    const title=String(record.title||'').trim(),source=record.source_url||record.url||'';
    const when=Date.parse(record.published_at||'');
    if(!title||!matchesGame(title,game)||!KEYWORDS[kind].test(title))continue;
    if(!Number.isFinite(when)||when<period)continue;
    try{if(new URL(source).protocol!=='https:')continue;}catch{continue;}
    if(seen.has(source))continue;
    seen.add(source);
    result.push({title:title.slice(0,280),url:source,published_at:new Date(when).toISOString(),
      publisher:String(record.publisher||'').slice(0,90),
      date_status:'資料庫來源刊登日期；活動起訖請核對原文'});
  }
  return result.sort((a,b)=>b.published_at.localeCompare(a.published_at)).slice(0,25);
}
async function snapshotLookup(request,env,game,kind){
  const [sources,latest,channels]=await Promise.all([
    getStored(env,request,'source_leads'),
    getStored(env,request,'latest'),
    getStored(env,request,'channel_history'),
  ]);
  const entries=savedMatches(game,kind,sources,latest,channels);
  return reply({game,kind,checked_at:new Date().toISOString(),status:'ok',
    source_mode:'scheduled_cache',updated_at:latest?.updated_at||sources?.updated_at||'',
    note:'即時 RSS 暫不可用，已使用 GitHub Actions 定時收集的最近10天公開資訊。無資料不代表沒有活動；刊登日期不是活動起迄時間。',
    entries});
}

async function lookup(request,env){
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
      source_mode:'live_rss',note:'這些是最近10天的公開原文線索；刊登日期不是活動開始日期。僅有已核實的活動起訖時間才應顯示為確定日期。',
      entries});
  }catch(e){
    try{
      return await snapshotLookup(request,env,game,kind);
    }catch(snapshotError){
      return reply({game,kind,checked_at:new Date().toISOString(),status:'unavailable',
        source_mode:'unavailable',error:'即時新聞來源及定時資料快照皆暫時無法讀取。',entries:[]},503);
    }
  }
}

/** Personal watchlists: random browser-held capability, isolated SQLite-backed DO.
 * Anyone with the random key can access that one list. Do not put keys in URLs.
 * Google News RSS is fetched only for bounded plain-text game names.
 */
const WATCH_INTERVAL=3*60*60*1000;
const WATCH_DATE_RE=/20\d{2}[-/.年](?:0?[1-9]|1[0-2])[-/.月](?:0?[1-9]|[12]\d|3[01])/g;
const WATCH_PERIOD_RE=/活動期間|活動時間|舉辦期間|event period|event dates?/i;
const WATCH_EVENT_RE=/活動|聯動|限時|慶典|週年|周年|賽季|event|collab|festival/i;
const WATCH_MAX_GAMES=25;
function watchJSON(value,status=200){
  return new Response(JSON.stringify(value),{status,headers:{
    'Content-Type':'application/json; charset=utf-8',
    'Cache-Control':'no-store',
    'X-Content-Type-Options':'nosniff'
  }});
}
function calendarDates(text){
  const marker=String(text||'').match(WATCH_PERIOD_RE);
  if(!marker)return ['',''];
  const portion=String(text).slice(marker.index,marker.index+160);
  const full=[...portion.matchAll(WATCH_DATE_RE)].slice(0,2).map(x=>x[0].replace(/[年月./]/g,'-').replace(/日/g,''));
  if(full.length<2)return ['',''];
  try{
    const dates=full.map(x=>{
      let p=x.split('-').map(Number);
      const d=new Date(Date.UTC(p[0],p[1]-1,p[2]));
      return d.getUTCFullYear()===p[0]&&d.getUTCMonth()===p[1]-1&&d.getUTCDate()===p[2]
        ?p[0]+'-'+String(p[1]).padStart(2,'0')+'-'+String(p[2]).padStart(2,'0'):'';
    });
    const span=(Date.parse(dates[1])-Date.parse(dates[0]))/86400000;
    if(!dates.every(Boolean)||span<0||span>150)return ['',''];
    return dates;
  }catch{return ['','']}
}
function watchNews(xml,game,now=Date.now()){
  const results=[],seen=new Set(),limit=now-32*86400000;
  for(const match of String(xml).matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)){
    const body=match[1],title=tag(body,'title'),source=tag(body,'link'),description=tag(body,'description');
    if(!title||!source||!title.normalize('NFKC').toLowerCase().includes(game.normalize('NFKC').toLowerCase())||!WATCH_EVENT_RE.test(title))continue;
    const published=new Date(tag(body,'pubDate')).getTime();
    if(!Number.isFinite(published)||published<limit||published>now+86400000)continue;
    let u;
    try{u=new URL(source);if(u.protocol!=='https:')continue}catch{continue}
    if(seen.has(u.href))continue;
    seen.add(u.href);
    const dates=calendarDates(title+' '+description);
    results.push({id:game+'|'+u.href,game,title:title.slice(0,200),source_url:u.href,
      published_at:new Date(published).toISOString(),
      start_date:dates[0],end_date:dates[1],
      date_status:dates[0]?'來源明示日期，建議核對':'日期待公布'});
    if(results.length>=30)break;
  }
  return results;
}
async function fetchWatchRSS(game){
  const url=new URL('https://news.google.com/rss/search');
  const q='"'+game+'" (遊戲活動 OR 限時活動 OR 聯動 OR 慶典) when:30d';
  for(const [k,v] of Object.entries({q,hl:'zh-TW',gl:'TW',ceid:'TW:zh-Hant'}))url.searchParams.set(k,v);
  const r=await fetch(url.toString(),{headers:{'User-Agent':'GameIntelWatchlist/2.0','Accept':'application/rss+xml,text/xml'},
    signal:AbortSignal.timeout(11000)});
  if(!r.ok)throw Error('RSS HTTP '+r.status);
  const body=await r.text();
  if(body.length>1300000)throw Error('RSS too large');
  return watchNews(body,game);
}
export class GameWatchlist{
  constructor(state,env){this.ctx=state;this.env=env}
  async fetch(request){
    const method=request.method,storage=this.ctx.storage;
    const games=await storage.get('games')||[];
    if(method==='GET'){
      return watchJSON({status:'ok',source_mode:'persistent_cloud',
        games,items:await storage.get('events')||[],
        updated_at:await storage.get('updated_at')||'',
        last_scan_at:await storage.get('last_scan_at')||'',
        errors:await storage.get('errors')||[]});
    }
    if(method!=='POST'&&method!=='DELETE')return watchJSON({error:'Unsupported method'},405);
    let raw;
    try{raw=await request.text();if(raw.length>1800)throw Error('Body too large')}catch{return watchJSON({error:'Invalid request'},400)}
    let body;
    try{body=JSON.parse(raw)}catch{return watchJSON({error:'Invalid JSON'},400)}
    const name=String(body?.name||'').trim();
    if(name.length<2||name.length>65||/[<>\u0000-\u001f]/.test(name))return watchJSON({error:'遊戲名稱格式不正確'},400);
    const source=String(body?.source_url||'').trim();
    if(source){
      try{
        let u=new URL(source);
        if(u.protocol!=='https:'||u.username||u.password||source.length>600)throw Error('invalid');
      }catch{return watchJSON({error:'請使用正確的 https 網址'},400)}
    }
    const key=name.normalize('NFKC').toLowerCase();
    if(method==='DELETE'){
      const revised=games.filter(x=>x.name.normalize('NFKC').toLowerCase()!==key);
      await storage.put('games',revised);
      const previous=await storage.get('events')||[];
      await storage.put('events',previous.filter(x=>x.game.normalize('NFKC').toLowerCase()!==key));
      if(!revised.length)await storage.deleteAlarm();
      return watchJSON({status:'ok',games:revised});
    }
    if(games.some(x=>x.name.normalize('NFKC').toLowerCase()===key)){
      return watchJSON({status:'already_tracking',games});
    }
    if(games.length>=WATCH_MAX_GAMES)return watchJSON({error:'每個追蹤清單最多 25 款遊戲'},409);
    const next=[...games,{name,source_url:source,added_at:new Date().toISOString()}];
    await storage.put('games',next);
    if(await storage.getAlarm()===null)await storage.setAlarm(Date.now()+1500);
    return watchJSON({status:'saved',games:next,monitoring:'scheduled'},201);
  }
  async alarm(){
    const storage=this.ctx.storage;
    try{
      const games=await storage.get('games')||[];
      if(!games.length)return;
      const prior=await storage.get('events')||[];
      const byId=new Map(prior.map(x=>[x.id,x]));
      const errors=[];
      for(let i=0;i<games.length;i+=3){
        const batch=await Promise.allSettled(games.slice(i,i+3).map(x=>fetchWatchRSS(x.name)));
        batch.forEach((result,j)=>{
          if(result.status==='fulfilled'){
            for(const event of result.value){
              const previous=byId.get(event.id);
              byId.set(event.id,{...event,first_seen_at:previous?.first_seen_at||new Date().toISOString()});
            }
          }else errors.push({game:games[i+j].name,error:String(result.reason||'').slice(0,140)});
        });
      }
      const cutoff=Date.now()-120*86400000;
      const active=new Set(games.map(g=>g.name.normalize('NFKC').toLowerCase()));
      const rows=[...byId.values()].filter(x=>active.has(x.game.normalize('NFKC').toLowerCase())
        &&Date.parse(x.published_at)>=cutoff).sort((a,b)=>b.published_at.localeCompare(a.published_at)).slice(0,500);
      await storage.put('events',rows);
      await storage.put('errors',errors);
      await storage.put('last_scan_at',new Date().toISOString());
      await storage.put('updated_at',new Date().toISOString());
    }finally{
      const games=await storage.get('games')||[];
      if(games.length)await storage.setAlarm(Date.now()+WATCH_INTERVAL);
    }
  }
}

export {parseRSS,decoded,matchesGame,savedMatches};
export default{
  async fetch(request,env){
    const url=new URL(request.url);
    if(url.pathname==='/api/watchlist'){
      if(!env?.WATCHLIST)return watchJSON({error:'雲端持久化追蹤尚未完成部署',status:'unavailable'},503);
      const key=request.headers.get('X-Watch-Key')||'';
      if(!/^[a-f0-9]{32,64}$/i.test(key))return watchJSON({error:'追蹤識別碼格式錯誤'},400);
      if(request.method!=='GET'){
        const origin=request.headers.get('Origin')||'';
        if(origin!==url.origin)return watchJSON({error:'不接受跨站修改'},403);
      }
      const stub=env.WATCHLIST.getByName(key.toLowerCase());
      try{return await stub.fetch(request)}catch(e){
        return watchJSON({error:'雲端追蹤服務暫時無法使用，資料未儲存',status:'error'},503);
      }
    }
    if(url.pathname==='/api/lookup'){
      if(request.method!=='GET')return reply({error:'僅接受 GET'},405);
      return lookup(request,env);
    }
    const response=await env.ASSETS.fetch(request);
    const headers=new Headers(response.headers);
    headers.set('X-Content-Type-Options','nosniff');
    headers.set('Referrer-Policy','strict-origin-when-cross-origin');
    return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
  }
};
