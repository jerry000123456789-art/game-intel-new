/* Mobile game business intelligence dashboard.
   Public snapshots; no unverifiable claims and no client-side credentials. */
(function(){
'use strict';
const $=id=>document.getElementById('gx-'+id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const goodUrl=value=>{try{let u=new URL(value);return u.protocol==='https:'?u.href:''}catch{return ''}};
const href=(url,title)=>goodUrl(url)?'<a class="gx-link" href="'+esc(goodUrl(url))+'" target="_blank" rel="noopener noreferrer">'+esc(title)+'</a>':'';
const toDate=value=>String(value||'').slice(0,10);
const ts=value=>{let v=Date.parse(value||'');return Number.isFinite(v)?v:0};
const dateTW=value=>value?new Date(value).toLocaleDateString('zh-TW',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}):'';
const nowDay=()=>new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Taipei'});
const dayDelta=value=>value?(Date.parse(toDate(value)+'T00:00:00Z')-Date.parse(nowDay()+'T00:00:00Z'))/86400000:null;
const gameKey=name=>String(name||'').normalize('NFKC').toLowerCase().replace(/潛水小漁夫|潜水小渔夫/gi,'').replace(/[\s\u3000:：·\-—「」『』()（）!！,，.。]/g,'');
const data={games:[],matrix:[],curated:[],codes:[],content:[],events:[],announcements:[],cloudGames:[],updated:'',channels:[],status:{}};
const ui={page:'home',window:'recent',month:new Date(),gameRows:[],codeRows:[],contentRows:[],brand:'',pending:[]};
ui.month.setDate(1);
try{ui.brand=localStorage.getItem('game-intel-brand')||'';ui.pending=JSON.parse(localStorage.getItem('game-intel-pending')||'[]')}catch{}
const repo='https://github.com/jerry000123456789-art/game-intel-new';
const names={home:'今日商機',games:'新遊戲雷達',codes:'最新兌換碼',content:'攻略／創作者情報',calendar:'我的活動追蹤',studio:'多平台文案工作台'};
const empty=message=>'<div class="gx-empty">'+esc(message)+'</div>';
function show(page){
  if(!Object.prototype.hasOwnProperty.call(names,page))return;
  ui.page=page;
  document.querySelectorAll('.gx-page').forEach(x=>x.classList.toggle('active',x.id==='gx-'+page));
  document.querySelectorAll('[data-gx-page]').forEach(x=>x.classList.toggle('active',x.dataset.gxPage===page));
  $('page-title').textContent=names[page];
  if(page==='games')renderGames();
  if(page==='calendar')renderCalendar();
  if(page==='studio'&&!$('studio-output').value)$('studio-output').placeholder='填入遊戲情報後，即可產生不同平台的原創宣傳草稿。';
  window.scrollTo({top:0,behavior:'smooth'});
}
function openCampaign(record){
  $('studio-game').value=record.game||'';
  $('studio-topic').value=record.title||'';
  $('studio-facts').value=record.facts||'';
  $('studio-source').value=record.url||'';
  $('selected-source').textContent='已帶入：'+(record.title||record.game||'宣傳主題');
  $('studio-output').value='';
  show('studio');
}
function dateLabel(row){
  if(!row.date)return '首次上市日期待確認';
  return row.date+(row.dateScope?' · '+row.dateScope:'');
}
function appId(url){
  try{
    let u=new URL(url);
    if(u.hostname==='play.google.com')return 'Android|'+(u.searchParams.get('id')||'');
    if(u.hostname==='apps.apple.com'){let m=u.pathname.match(/\/id(\d+)/);return m?'iOS|'+m[1]:''}
  }catch{}
  return '';
}
function platformRow(r,mapping){
  const platform=(r.platforms||[])[0];
  if(platform!=='Google Play'&&platform!=='App Store')return null;
  const country=String(r.country||((r.region==='台灣')?'TW':'US')).toUpperCase();
  const source=r.source_url||r.store_links?.[0]?.url||'';
  let platformId=appId(source),platformType=platform==='Google Play'?'Android':'iOS';
  const k=platformType+'|'+platformId.split('|')[1]+'|'+country;
  const evidence=mapping.get(k)||{};
  const date=evidence.store_release_date||r.release_date||'';
  const dateScope=platform==='App Store'?'Apple 產品發行日期，非各國獨立首發':evidence.release_source_type||'Google Play 商店發行紀錄';
  return {platform,country,date,dateScope,source,proof:evidence.country_launch_source||source,
    cover:r.cover_url||evidence.cover_url||'',status:r.status||'商店收錄',
    preOrder:!!evidence.preorder_confirmed};
}
function gameRecords(){
  const lookup=new Map();
  for(const x of data.matrix){
    if(x.app_id&&x.platform&&x.country)lookup.set(x.platform+'|'+x.app_id+'|'+x.country,x);
  }
  const games=new Map();
  function add(name,p,art,developer,featured=false){
    const key=gameKey(name);
    if(!key||!p)return;
    if(!games.has(key))games.set(key,{key,name,platforms:[],cover:'',developer:'',featured:false});
    const game=games.get(key);
    if(featured){game.name=name;game.featured=true}
    if(!game.cover&&art)game.cover=art;
    if(!game.developer&&developer)game.developer=developer;
    const id=p.platform+'|'+p.country+'|'+(p.source||'');
    if(!game.platforms.some(x=>x.platform+'|'+x.country+'|'+(x.source||'')===id))game.platforms.push(p);
  }
  for(const r of data.games){
    const pr=platformRow(r,lookup);
    if(pr)add(r.name,pr,r.cover_url||pr.cover,r.developer||'');
  }
  for(const g of data.curated){
    for(const p of g.platforms||[]){
      add(g.name,{platform:p.platform,country:p.country,date:p.date||'',
        dateScope:p.date_scope||'',source:p.store_url||'',proof:p.evidence_url||p.store_url,
        status:p.date?'已上市':'商店收錄',preOrder:false},g.cover_url||'',g.developer||'',true);
    }
  }
  return [...games.values()];
}
function gameDateRows(game,filterMarket='all',filterStore='all'){
  return game.platforms.filter(x=>(filterStore==='all'||x.platform===filterStore)
    &&(filterMarket==='all'||(filterMarket==='TW'&&x.country==='TW')||(filterMarket==='US'&&x.country!=='TW'&&x.country!=='HW')||(filterMarket==='HW'&&x.platform==='AppGallery')));
}
function gameStatus(rows){
  const dates=rows.filter(x=>x.date).map(x=>({row:x,diff:dayDelta(x.date)}));
  let upcoming=dates.filter(x=>x.diff>0).sort((a,b)=>a.diff-b.diff);
  let recent=dates.filter(x=>x.diff<=0&&x.diff>=-30).sort((a,b)=>b.diff-a.diff);
  if(rows.some(x=>x.preOrder))return {type:'upcoming',date:upcoming[0]?.row?.date||'',label:'預先註冊'};
  if(upcoming.length)return {type:'upcoming',date:upcoming[0].row.date,label:'即將上市'};
  if(recent.length)return {type:'recent',date:recent[0].row.date,label:'新上市'};
  let anyDate=dates.filter(x=>x.diff<=0).sort((a,b)=>b.diff-a.diff);
  if(anyDate.length)return {type:'history',date:anyDate[0].row.date,label:'已上市'};
  if(rows.some(x=>x.status==='即將上市'||x.status==='預先註冊'))return {type:'upcoming',date:'',label:'預約／日期待公布'};
  return {type:'history',date:'',label:'商店收錄'};
}
function filteredGames(){
  const q=$('game-q').value.trim().toLowerCase(),market=$('game-market').value,store=$('game-store').value;
  let out=[];
  for(const game of gameRecords()){
    if(q&&!(game.name+' '+game.developer).toLowerCase().includes(q))continue;
    const rows=gameDateRows(game,market,store);
    if(!rows.length)continue;
    const st=gameStatus(rows);
    if(ui.window!==st.type)continue;
    out.push({game,rows,status:st});
  }
  const byDate=x=>x.status.date||(ui.window==='upcoming'?'9999-12-31':'0000-00-00');
  const reverse=$('game-order').value==='old';
  out.sort((a,b)=>{
    const aDate=byDate(a),bDate=byDate(b);
    if(ui.window==='upcoming')return reverse?bDate.localeCompare(aDate):aDate.localeCompare(bDate);
    return reverse?aDate.localeCompare(bDate):bDate.localeCompare(aDate);
  });
  return out;
}
function gameCard(rec,index){
  const g=rec.game,st=rec.status;
  const picture=g.cover?'<img loading="lazy" src="'+esc(goodUrl(g.cover))+'" alt="'+esc(g.name)+'" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\'"><span class="gx-image-fallback" style="display:none">官方圖片暫時無法載入</span>':
    '<div class="gx-image-fallback">🎮<br>官方圖片擷取中</div>';
  const labels=rec.rows.map(x=>'<span class="gx-pill">'+esc(x.platform==='App Store'?'iOS':x.platform==='Google Play'?'Android':x.platform)+' · '+esc(x.country==='TW'?'台灣':x.country==='US'?'美國':x.country==='JP'?'日本':x.country==='KR'?'韓國':x.country)+'</span>').join('');
  const evidence=rec.rows.filter(x=>x.date).slice(0,4).map(x=>'<div class="gx-card-description">'+esc(x.platform==='App Store'?'iOS':x.platform==='Google Play'?'Android':x.platform)+' '+esc(x.date)+' · '+esc(x.dateScope)+'</div>').join('');
  return '<article class="gx-card"><div class="gx-art">'+picture+'</div><div class="gx-card-body"><h3 class="gx-card-name">'+esc(g.name)+'</h3>'
     +'<div class="gx-pills"><span class="gx-pill '+(st.type==='recent'?'green':st.type==='upcoming'?'amber':'')+'">'+esc(st.label)+'</span>'+labels+'</div>'
     +(evidence||'<p class="gx-card-description">首次上市日期待確認</p>')
     +'<div class="gx-card-actions"><button class="gx-btn primary small" data-gx-game-campaign="'+index+'">製作文案</button>'
     +'<button class="gx-btn small" data-gx-game-detail="'+index+'">查看發布來源</button></div></div></article>';
}
function renderGames(){
  ui.gameRows=filteredGames();
  $('game-count').textContent=ui.gameRows.length+' 款符合條件的遊戲 · 來源日期與首次發現時間分開；各國獨立首發日未核實時不推定。';
  const limited=ui.gameRows.slice(0,180);
  $('game-list').innerHTML=limited.length?limited.map(gameCard).join(''):empty($('game-market').value==='HW'||$('game-store').value==='AppGallery'
      ?'華為 AppGallery 的官方商店清單仍無法穩定讀取，尚未取得可核實的手機遊戲。':'目前沒有符合這個日期範圍的遊戲。可切換歷史資料或修改篩選。');
  $('game-list').querySelectorAll('[data-gx-game-campaign]').forEach(x=>x.addEventListener('click',()=>{
    const item=ui.gameRows[Number(x.dataset.gxGameCampaign)];
    openCampaign({game:item.game.name,title:item.game.name+' · '+item.status.label,
      facts:item.rows.filter(x=>x.date).map(x=>(x.platform==='App Store'?'iOS':'Android')+'：'+x.date+'（'+x.dateScope+'）').join('\n')
        ||'商店已收錄，精確首次發布日期待查',
      url:item.rows.find(x=>goodUrl(x.proof))?.proof||item.rows[0]?.source||''});
  }));
  $('game-list').querySelectorAll('[data-gx-game-detail]').forEach(x=>x.addEventListener('click',()=>{
    const item=ui.gameRows[Number(x.dataset.gxGameDetail)];
    const lines=item.rows.map(y=>y.platform+' / '+y.country+' / '+dateLabel(y)+'\n'+(y.proof||y.source||'')).join('\n\n');
    let message=lines||'尚無商店來源';
    window.alert(item.game.name+'\n\n'+message);
  }));
}
function sortedCodes(){
  let seen=new Set(),out=[];
  for(const c of data.codes){
    if(!c.game||!c.code||c.expired===true)continue;
    const code=String(c.code).trim(),key=gameKey(c.game)+'|'+code.toLowerCase();
    if(!/^[A-Za-z0-9_-]{4,35}$/.test(code)||seen.has(key))continue;
    seen.add(key);out.push(c);
  }
  return out.sort((a,b)=>ts(b.discovered_at)-ts(a.discovered_at));
}
function renderCodes(){
  let q=$('code-q').value.trim().toLowerCase();
  let codes=sortedCodes().filter(x=>!q||(x.game+' '+x.code).toLowerCase().includes(q));
  if($('code-order').value==='old')codes.reverse();
  ui.codeRows=codes;
  $('code-list').innerHTML=codes.length?codes.slice(0,100).map((c,i)=>'<article class="gx-feed-item"><div class="gx-feed-icon">🎁</div><div class="gx-grow"><h3>'+esc(c.game)+'</h3>'
    +'<div class="gx-code">'+esc(c.code)+'</div><div class="gx-meta">發現：'+esc(dateTW(c.discovered_at))+' · 公開代碼（未實測）</div>'
    +'<div class="gx-actions"><button class="gx-btn primary small" data-gx-copy-code="'+i+'">複製代碼</button>'
    +'<button class="gx-btn small" data-gx-code-campaign="'+i+'">製作宣傳</button>'+href(c.source_url,'查看來源')+'</div></div></article>').join('')
    :empty('目前沒有符合名稱的公開代碼；可嘗試其他遊戲。');
  $('code-list').querySelectorAll('[data-gx-copy-code]').forEach(x=>x.addEventListener('click',()=>copyText(codes[Number(x.dataset.gxCopyCode)].code)));
  $('code-list').querySelectorAll('[data-gx-code-campaign]').forEach(x=>x.addEventListener('click',()=>{
    const c=codes[Number(x.dataset.gxCodeCampaign)];
    openCampaign({game:c.game,title:'新兌換碼公開資訊',facts:'公開兌換碼：'+c.code+'\n來源於 '+dateTW(c.discovered_at)+' 收錄，尚未在遊戲內實測。',url:c.source_url});
  }));
}
function contentEntries(){
  const map=new Map();
  for(const x of data.content){
    const url=x.url||x.source_url||'';
    if(!goodUrl(url)||!x.title)continue;
    const when=ts(x.published_at||x.updated_at);
    if(when && when<Date.now()-31*86400000)continue;
    const key=url;
    if(!map.has(key))map.set(key,{title:x.title,game:x.game||'',url,
      publisher:x.publisher||'',published_at:x.published_at||x.updated_at||'',
      category:x.category||x.kind||'',origin:x.origin||''});
  }
  return [...map.values()].sort((a,b)=>ts(b.published_at)-ts(a.published_at));
}
function contentType(x){
  if(x.origin==='YouTube'||x.category==='影片情報'||/youtube\.com|youtu\.be/i.test(x.url))return 'YouTube';
  if(/攻略|新手|配隊|教學|guide|build|walkthrough|tier list/i.test(x.title+' '+x.category))return '攻略';
  return '新聞';
}
function renderContent(){
  const q=$('content-q').value.trim().toLowerCase(),kind=$('content-kind').value;
  let list=contentEntries().filter(x=>(kind==='all'||contentType(x)===kind)
    &&(!q||(x.title+' '+x.game+' '+x.publisher).toLowerCase().includes(q)));
  if($('content-order').value==='old')list.reverse();
  ui.contentRows=list;
  $('content-count').textContent=list.length+' 則';
  $('content-list').innerHTML=list.length?list.slice(0,120).map((x,i)=>
     '<article class="gx-feed-item"><div class="gx-feed-icon">'+(contentType(x)==='YouTube'?'🎬':contentType(x)==='攻略'?'📖':'📰')+'</div>'
     +'<div class="gx-grow"><h3>'+esc(x.title)+'</h3><div class="gx-meta">'+esc(x.publisher||contentType(x))+' · '+esc(dateTW(x.published_at))+'</div>'
     +'<div class="gx-actions">'+href(x.url,'查看原文')+' <button class="gx-btn primary small" data-gx-content-campaign="'+i+'">製作宣傳</button></div></div></article>').join('')
     :empty('這個條件下暫無新情報。');
  $('content-list').querySelectorAll('[data-gx-content-campaign]').forEach(btn=>btn.addEventListener('click',()=>{
    let x=list[Number(btn.dataset.gxContentCampaign)];
    openCampaign({game:x.game,title:x.title,facts:'創作者／新聞來源：'+(x.publisher||'公開來源')+
      '\n刊登日期：'+dateTW(x.published_at)+'\n請先閱讀原文，補充已確認的遊戲資訊後再發表。',url:x.url});
  }));
  $('creators').innerHTML=data.channels.map((id,i)=>href('https://www.youtube.com/channel/'+encodeURIComponent(id),
    i===data.channels.length-1?'新增指定頻道':'已追蹤頻道 '+(i+1))).join(' · ')||'尚未設定頻道';
}
function trackedNames(){
  const names=new Set(data.cloudGames.map(x=>gameKey(x.name)));
  return data.cloudGames.concat(ui.pending.filter(x=>!names.has(gameKey(x.name))));
}
function persistPending(){try{localStorage.setItem('game-intel-pending',JSON.stringify(ui.pending.slice(-30)))}catch{}}
function renderWatchList(){
  const cloud=new Set(data.cloudGames.map(g=>gameKey(g.name)));
  ui.pending=ui.pending.filter(x=>!cloud.has(gameKey(x.name)));persistPending();
  const all=trackedNames();
  $('watch-list').innerHTML=all.length?'<div class="gx-muted" style="margin-top:14px">目前追蹤清單</div>'+
    all.map(x=>'<div class="gx-watch-item"><div><strong>'+esc(x.name)+'</strong><div class="gx-muted">'+(cloud.has(gameKey(x.name))?'已加入雲端自動追蹤':'尚未確認 GitHub 提交')+'</div></div>'
      +(!cloud.has(gameKey(x.name))?'<a class="gx-btn small" target="_blank" rel="noopener noreferrer" href="'+esc(watchIssueLink(x))+'">送出追蹤</a>':'<span class="gx-pill green">監控中</span>')+'</div>').join('')
    :'<p class="gx-muted" style="margin-top:18px">尚未新增追蹤遊戲。新增後，雲端爬蟲才會掃描該遊戲的活動公告。</p>';
}
function watchIssueLink(x){
  const title='[追蹤遊戲] '+x.name;
  const body='遊戲名稱：'+x.name+'\n來源：'+(x.url||'')+'\n\n請確認後提交 Issue，雲端會在工作流程執行後開始追蹤。';
  return repo+'/issues/new?title='+encodeURIComponent(title)+'&body='+encodeURIComponent(body);
}
function calendarItems(){
  const watched=new Set(trackedNames().map(x=>gameKey(x.name)));
  let result=[];
  for(const x of data.events){
    if(!watched.has(gameKey(x.game)))continue;
    if(!x.start_at||!x.end_at)continue;
    result.push({game:x.game,title:x.title,start:toDate(x.start_at),end:toDate(x.end_at),url:x.source_url});
  }
  for(const x of data.announcements){
    if(!watched.has(gameKey(x.game))||!x.start_date||!x.end_date)continue;
    result.push({game:x.game,title:x.title,start:x.start_date,end:x.end_date,url:x.source_url});
  }
  return result;
}
function renderCalendar(){
  renderWatchList();
  const list=calendarItems(),y=ui.month.getFullYear(),m=ui.month.getMonth();
  $('month-label').textContent=y+' 年 '+(m+1)+' 月';
  const first=new Date(y,m,1),last=new Date(y,m+1,0).getDate();
  let cells=['日','一','二','三','四','五','六'].map(x=>'<div class="gx-muted" style="text-align:center">'+x+'</div>');
  const start=first.getDay();
  for(let i=0;i<start;i++)cells.push('<div class="gx-day outside"></div>');
  for(let day=1;day<=last;day++){
    const date=y+'-'+String(m+1).padStart(2,'0')+'-'+String(day).padStart(2,'0');
    const relevant=list.filter(x=>x.start<=date&&x.end>=date);
    cells.push('<div class="gx-day"><span class="day-num">'+day+'</span>'+
      relevant.slice(0,3).map(x=>'<span class="event-chip" title="'+esc(x.game+'｜'+x.title)+'">'+esc(x.game)+'</span>').join('')
      +(relevant.length>3?'<span class="gx-muted">+'+(relevant.length-3)+'</span>':'')+'</div>');
  }
  $('calendar-view').innerHTML='<div class="gx-calendar-grid">'+cells.join('')+'</div>'+
    (list.length?'<div class="gx-stack" style="margin-top:17px">'+list.filter(x=>x.start<=y+'-'+String(m+1).padStart(2,'0')+'-'+String(last).padStart(2,'0')
      &&x.end>=y+'-'+String(m+1).padStart(2,'0')+'-01').map(x=>
      '<div class="gx-feed-item"><div class="gx-grow"><strong>'+esc(x.game)+' · '+esc(x.title)+'</strong><div class="gx-meta">'+esc(x.start)+' 至 '+esc(x.end)+'</div>'
      +href(x.url,'查看公告')+'</div></div>').join('')+'</div>':empty('本月沒有已核對日期的追蹤遊戲活動。'));
  const watched=new Set(trackedNames().map(x=>gameKey(x.name)));
  const news=data.announcements.filter(x=>watched.has(gameKey(x.game))&&!x.start_date).slice(0,35);
  $('calendar-undated').innerHTML=news.length?news.map(x=>
    '<div class="gx-feed-item"><div class="gx-feed-icon">📣</div><div><h3>'+esc(x.game+' · '+x.title)+'</h3><div class="gx-meta">'+esc(dateTW(x.published_at))+' · 日期尚未公布</div>'
      +href(x.source_url,'查看公告')+'</div></div>').join(''):empty('目前沒有待確認的活動預告，或尚未加入追蹤遊戲。');
}
function teaser(x){
  return '<div class="gx-feed-item"><div class="gx-grow"><h3>'+esc(x.title||x.game||'情報')+'</h3>'
   +'<div class="gx-meta">'+esc(x.sub||'')+'</div>'
   +(x.url?href(x.url,'查看來源'):'')+'</div></div>';
}
function renderHome(){
  let games=gameRecords().map(game=>({game,rows:game.platforms,status:gameStatus(game.platforms)}))
     .filter(x=>x.status.type==='recent').sort((a,b)=>(b.status.date||'').localeCompare(a.status.date||''));
  let upcoming=gameRecords().filter(x=>gameStatus(x.platforms).type==='upcoming');
  $('kpi-new').textContent=games.length;
  $('kpi-soon').textContent=upcoming.length;
  $('kpi-code').textContent=sortedCodes().length;
  $('kpi-watch').textContent=data.cloudGames.length;
  $('overview-games').innerHTML=games.length?games.slice(0,6).map(x=>teaser({title:x.game.name,sub:x.status.date+' · '+x.status.label,
    url:x.rows.find(y=>y.date===x.status.date)?.source||x.rows[0]?.source})).join(''):empty('最近 30 天沒有可確認日期的新遊戲。');
  $('overview-codes').innerHTML=sortedCodes().slice(0,5).map(x=>teaser({title:x.game+' · '+x.code,
    sub:dateTW(x.discovered_at),url:x.source_url})).join('')||empty('尚無新兌換碼。');
  $('overview-content').innerHTML=contentEntries().slice(0,7).map(x=>teaser({title:x.title,sub:(x.publisher||x.category)+' · '+dateTW(x.published_at),url:x.url})).join('')||empty('尚無最新情報。');
}
async function copyText(text){
  try{
    if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(text);
    else{const input=document.createElement('textarea');input.value=text;document.body.appendChild(input);input.select();document.execCommand('copy');input.remove()}
    const info=$('footer');info.textContent='✓ 已複製到剪貼簿';setTimeout(()=>info.textContent='公開資料僅供情報參考 · 請核對來源與使用資格',1700);
  }catch{window.alert('無法存取剪貼簿，請選取文案後手動複製。')}
}
function draftText(){
  const game=$('studio-game').value.trim(),topic=$('studio-topic').value.trim(),facts=$('studio-facts').value.trim(),
    src=goodUrl($('studio-source').value.trim()),brand=$('studio-brand').value.trim(),
    platform=$('studio-platform').value,angle=$('studio-angle').value;
  if(!game&&!topic)return '';
  const title=(game?('【'+game+'】'):'')+(topic||'最新情報');
  const hook=angle==='curious'?'這則消息有什麼值得注意？':angle==='timely'?'最新情報整理，想追消息的玩家可以先收藏。':'整理重點，讓你少花時間找資料。';
  const body=facts||'請依照原始來源補充確定的內容，再發布。';
  const attribution=src?'\n\n原始資料：'+src:'\n\n資料來源：請補入公告或創作者原文';
  const signature=brand?'\n\n'+brand+'｜遊戲情報整理':'';
  const tag=game?'#'+game.replace(/\s/g,'')+' ':'';
  const option={
    'Dcard':title+'\n\n'+hook+'\n\n這篇整理目前找到的公開資訊：\n'+body+
      '\n\n你們最在意這次的哪個變化？\n\n※ 商業資訊整理，請依板規選擇適當方式發布。',
    '痞客邦':title+'｜最新整理與常見問題\n\n'+hook+'\n\n一、這次有什麼消息？\n'+body+
      '\n\n二、玩家可以先確認什麼？\n核對活動日期、伺服器、使用限制與官方公告。\n\n三、常見問題\nQ：資訊還有效嗎？\nA：以官方即時公告為準。',
    '巴哈姆特':title+'\n\n【資訊來源與整理】\n'+body+
      '\n\n【需要注意】\n活動日期／兌換資格若有更改以官方公告為準。\n\n歡迎玩家補充正確資訊。涉及商業服務請依哈啦板規範發布，不偽裝成一般心得。',
    'Facebook':'🎮 '+title+'\n\n'+hook+'\n\n'+body+
      '\n\n📌 留著這篇方便需要時查看；也可以分享給正在玩的朋友。',
    'Instagram':'🎮 '+title+'\n\n📌 第 1 張：最新情報重點\n📌 第 2 張：'+body+
      '\n📌 第 3 張：如何確認活動或使用資格\n\n收藏這份整理，下次不用重找。\n\n'+tag+'#手機遊戲 #遊戲情報',
    'Threads':title+'\n\n'+hook+'\n'+body+'\n\n你會先關注哪一點？\n\n'+tag+'#遊戲資訊',
    'YouTube Shorts':'【15–45 秒短影音腳本】\n0–3 秒：'+title+
      '\n3–12 秒：'+hook+'\n12–35 秒：'+body+
      '\n35–45 秒：提醒觀眾保存資訊並查看原始公告。\n\n畫面建議：自製標題卡／官方可用素材／重點字幕。',
    'LINE 官方帳號':'🎮 '+title+'\n\n'+body+
      '\n\n想掌握新消息，可以保留這則通知；詳情請查看公告。',
    'TikTok':'【短影音分鏡】\n開頭 3 秒：'+title+
      '\n中段：'+body+'\n結尾：'+hook+
      '\n\n字幕：'+tag+'#遊戲攻略 #手機遊戲\n素材使用原創畫面或已授權內容。',
    'Discord':'**'+title+'**\n\n'+body+
      '\n\n玩家可以在這串留言補充更新。資訊有變動時將以原始公告核對。'
  }[platform]||title+'\n'+body;
  return option+attribution+signature;
}
function makeDraft(){
  const draft=draftText();
  if(!draft){window.alert('先輸入遊戲名稱或內容主題。');return}
  $('studio-output').value=draft;
  try{localStorage.setItem('game-intel-brand',$('studio-brand').value.trim())}catch{}
}
async function load(name){
  try{
    const response=await fetch('/data/'+name+'.json',{cache:'no-store'});
    if(!response.ok)throw new Error('HTTP '+response.status);
    return await response.json();
  }catch(e){console.warn('Data unavailable',name,e);return {}}
}
async function checkNewActivity(){
  const response=await load('tracked_events');
  const incoming=response.items||[];
  const names=new Set(data.cloudGames.map(x=>gameKey(x.name)));
  const relevant=incoming.filter(x=>names.has(gameKey(x.game)));
  let seen=[];
  try{seen=JSON.parse(localStorage.getItem('game-intel-activity-seen')||'[]')}catch{}
  const previously=new Set(seen),newOnes=relevant.filter(x=>x.id&&!previously.has(x.id));
  try{localStorage.setItem('game-intel-activity-seen',JSON.stringify(relevant.map(x=>x.id).filter(Boolean).slice(0,600)))}catch{}
  if(data.announcements.length||incoming.length){data.announcements=incoming;renderCalendar()}
  if(!seen.length||!newOnes.length)return;
  try{
    const enabled=localStorage.getItem('game-intel-activity-alerts')==='yes';
    if(!enabled||!('Notification' in window)||Notification.permission!=='granted')return;
    const item=newOnes[0];
    new Notification('新增遊戲活動：'+item.game,{body:item.title,tag:'game-intel-'+item.id});
  }catch{}
}
async function main(){
  const files=['game_catalog','release_matrix','featured_launches','codes','channel_history','latest','source_leads',
    'events','tracked_events','tracked_games','coverage_status'];
  const values=await Promise.all(files.map(load));
  const maps=Object.fromEntries(files.map((f,i)=>[f,values[i]]));
  data.games=maps.game_catalog.items||[];
  data.matrix=maps.release_matrix.items||[];
  data.curated=maps.featured_launches.items||[];
  data.codes=maps.codes.items||[];
  data.content=[...(maps.channel_history.items||[]),...(maps.latest.items||[]),...(maps.source_leads.items?.guides||[])];
  data.events=maps.events.items||[];
  data.announcements=maps.tracked_events.items||[];
  data.cloudGames=maps.tracked_games.games||[];
  data.updated=maps.game_catalog.updated_at||'';
  data.status=maps.coverage_status||{};
  data.channels=['UCOCtiyIH-Dt00Ntv-WqPgfw','UCNH35X4JoxqnZHRyWGI04Vg',
    'UC4c-wTOqEID-_vH4MhNs06w','UC-e2q_YhFnfsEggbJsTLPHg','UC_XZ4O10pZq9RCigggGSB1A'];
  $('sync-label').textContent='資料已載入';
  $('sync-date').textContent=data.updated?'更新：'+dateTW(data.updated):'同步資訊待確認';
  $('studio-brand').value=ui.brand;
  renderHome();renderGames();renderCodes();renderContent();renderCalendar();
  checkNewActivity();
  setInterval(checkNewActivity,15*60*1000);
  try{if(localStorage.getItem('game-intel-activity-alerts')==='yes'&&window.Notification?.permission==='granted')$('watch-alerts').textContent='活動提醒已開啟'}catch{}
}
document.querySelectorAll('[data-gx-page]').forEach(button=>button.addEventListener('click',()=>show(button.dataset.gxPage)));
document.querySelectorAll('[data-gx-jump]').forEach(button=>button.addEventListener('click',()=>{
  if(button.dataset.gxJump==='games-upcoming'){ui.window='upcoming';document.querySelectorAll('[data-gx-window]').forEach(x=>x.classList.toggle('active',x.dataset.gxWindow==='upcoming'));show('games')}
  else show(button.dataset.gxJump);
}));
document.querySelectorAll('[data-gx-window]').forEach(button=>button.addEventListener('click',()=>{
  ui.window=button.dataset.gxWindow;
  document.querySelectorAll('[data-gx-window]').forEach(x=>x.classList.toggle('active',x===button));
  renderGames();
}));
['game-q','game-market','game-store','game-order'].forEach(id=>$(id).addEventListener('input',renderGames));
['code-q','code-order'].forEach(id=>$(id).addEventListener('input',renderCodes));
['content-q','content-kind','content-order'].forEach(id=>$(id).addEventListener('input',renderContent));
$('watch-form').addEventListener('submit',event=>{
  event.preventDefault();
  const name=$('watch-name').value.trim(),url=$('watch-url').value.trim();
  if(name.length<2||name.length>65)return;
  if(url&&!goodUrl(url)){window.alert('官方網址必須是 https:// 連結。');return}
  if(!ui.pending.some(x=>gameKey(x.name)===gameKey(name))
    &&!data.cloudGames.some(x=>gameKey(x.name)===gameKey(name)))ui.pending.push({name,url});
  persistPending();renderCalendar();
  window.open(watchIssueLink({name,url}),'_blank','noopener,noreferrer');
  $('watch-name').value='';$('watch-url').value='';
});
$('watch-alerts').addEventListener('click',async()=>{
  if(!('Notification' in window)){window.alert('此瀏覽器不支援網站通知。');return}
  try{
    const permission=await Notification.requestPermission();
    if(permission==='granted'){
      try{localStorage.setItem('game-intel-activity-alerts','yes')}catch{}
      $('watch-alerts').textContent='活動提醒已開啟';
      window.alert('已啟用：此網站開啟期間，發現追蹤遊戲的新公告會通知。關閉網站後不會推播。');
    }else{window.alert('瀏覽器未授權通知，你仍可在行事曆查看公告。')}
  }catch{window.alert('無法啟用瀏覽器通知。')}
});
$('prev-month').addEventListener('click',()=>{ui.month.setMonth(ui.month.getMonth()-1);renderCalendar()});
$('next-month').addEventListener('click',()=>{ui.month.setMonth(ui.month.getMonth()+1);renderCalendar()});
$('generate').addEventListener('click',makeDraft);
$('use-draft').addEventListener('click',()=>{
  let input=$('studio-angle');input.selectedIndex=(input.selectedIndex+1)%input.options.length;makeDraft();
});
$('copy-draft').addEventListener('click',()=>copyText($('studio-output').value));
main().catch(error=>{console.error(error);$('sync-label').textContent='部分資料載入失敗，請重新整理'});
})();
