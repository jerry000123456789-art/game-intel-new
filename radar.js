/* Compact mobile games radar. Data: public official store URLs and conservative source evidence. */
const root=typeof document!=="undefined"?document:null;
const $=id=>root?.getElementById(id);
const twCountries={TW:"台灣",US:"美國",JP:"日本",KR:"韓國",HK:"香港",SG:"新加坡"};
const model={games:[],health:{},summary:{},store:"all",market:"all",category:"新上市",query:"",page:0,perPage:55,sort:"new"};
const norm=s=>String(s??"").normalize("NFKC").toLocaleLowerCase().replace(/[\s\p{P}\p{S}_]+/gu,"");
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeDate=s=>/^\d{4}-\d{2}-\d{2}$/.test(String(s||""))?s:"";
function normalizeQuery(s){
  const raw=String(s||"").trim();
  if(!raw)return "";
  try{
    const u=new URL(raw);
    if(u.hostname==="play.google.com")return u.searchParams.get("id")||raw;
    if(u.hostname==="apps.apple.com")return u.pathname.match(/\/id(\d+)/)?.[1]||raw;
  }catch{}
  return raw;
}
function searchMatches(g,q){
  if(!q)return true;
  const needle=norm(normalizeQuery(q));
  const words=[g.name,g.other_name,g.developer,...(g.aliases||[]),...(g.variants||[]).flatMap(v=>[v.name,v.id,v.source_url])];
  return words.some(w=>norm(w).includes(needle));
}
function selectedVariants(g,store="all",market="all"){
  return (g.variants||[]).filter(v=>(store==="all"||v.store===store)&&
    (market==="all"||market==="TW"&&v.country==="TW"||market==="INT"&&v.country!=="TW"));
}
function gameCategories(variants,today=new Date().toISOString().slice(0,10)){
  const recent=variants.some(v=>v.status==="已上市"&&safeDate(v.date)&&
    Math.round((Date.parse(today+"T00:00:00Z")-Date.parse(v.date+"T00:00:00Z"))/86400000)>=0&&
    Math.round((Date.parse(today+"T00:00:00Z")-Date.parse(v.date+"T00:00:00Z"))/86400000)<=30);
  const next=variants.some(v=>v.status==="即將上市");
  const pre=variants.some(v=>["預先註冊","預購"].includes(v.status));
  return [...(recent?["新上市"]:[]),...(next?["即將上市"]:[]),...(pre?["預約／預先註冊"]:[])];
}
function filtered(){
  let out=[];
  for(const game of model.games){
    if(!searchMatches(game,model.query))continue;
    const variants=selectedVariants(game,model.store,model.market);
    if(!variants.length)continue;
    // Searching covers all records, not just current category.
    if(!model.query&&model.category!=="全部遊戲"&&!gameCategories(variants).includes(model.category))continue;
    out.push({game,variants});
  }
  const date=x=>x.variants.map(v=>safeDate(v.date)).filter(Boolean).sort().pop()||x.game.first_seen_at?.slice(0,10)||"";
  out.sort((a,b)=>{
    const aDate=date(a),bDate=date(b);
    return model.sort==="old"?aDate.localeCompare(bDate):bDate.localeCompare(aDate);
  });
  return out;
}
function areaLine(platform,area,variants){
  const pre=variants.some(v=>v.status==="預先註冊"||v.status==="預購");
  const soon=variants.some(v=>v.status==="即將上市");
  const other=variants.some(v=>v.status==="已上市"||v.status==="商店有收錄");
  let note=pre&&other?"（部分預先註冊）":pre?"（"+(platform==="Android"?"預先註冊":"預購")+"）":
    soon&&other?"（各國上架時間不同）":soon?"（即將上市）":"";
  const dateRows=variants.filter(v=>safeDate(v.date));
  const uniq=[...new Set(dateRows.map(v=>v.date))];
  let dateText="";
  if(uniq.length===1){
    const date=uniq[0],status=dateRows[0].status;
    const label=pre&&dateRows.some(v=>["預先註冊","預購"].includes(v.status))?"預約上架時間":
      status==="即將上市"?"預計上架日期":"上架日期";
    dateText='<div class="platform-date">'+label+'：<strong>'+esc(date)+'</strong></div>';
  }else if(area==="台灣"&&uniq.length){
    // A single Taiwan market can have variant-specific dates across stores,
    // but this function receives a single platform, so prefer the same verified date.
    dateText='<div class="platform-date">上架日期：'+esc(uniq.sort().join("、"))+'</div>';
  }else if(uniq.length>1){
    dateText='<div class="platform-date">各國日期不同，請查看詳細資訊</div>';
  }
  return '<div class="platform-line"><div class="platform-label">'+esc(platform)+'｜'+esc(area)+
    '<span class="'+(pre?"prereg":"")+'">'+note+'</span></div>'+dateText+'</div>';
}
function platformLines(variants){
  const out=[];
  for(const platform of ["Android","iOS"]){
    const arr=variants.filter(v=>v.platform===platform);
    if(!arr.length)continue;
    const tw=arr.filter(v=>v.country==="TW"),other=arr.filter(v=>v.country!=="TW");
    if(tw.length)out.push(areaLine(platform,"台灣",tw));
    if(other.length)out.push(areaLine(platform,"國際",other));
  }
  return out.join("");
}
function makeRow(x,index){
  const g=x.game;
  let image=g.cover_url?'<img class="cover" loading="lazy" src="'+esc(g.cover_url)+'" alt="遊戲封面" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement(\'span\'),{className:\'cover cover-fallback\',textContent:\'🎮\'}))">':
    '<span class="cover cover-fallback" aria-hidden="true">🎮</span>';
  return '<article class="item">'+image+
    '<div><div class="name">'+esc(g.name)+'</div>'+
    (g.other_name?'<div class="secondary">其他名稱：'+esc(g.other_name)+'</div>':'')+
    '</div><div class="platforms">'+platformLines(x.variants)+'</div>'+
    '<button class="more" type="button" data-detail="'+esc(g.id)+'" aria-label="查看 '+esc(g.name)+' 的詳細資訊">詳細資訊 ›</button></article>';
}
function sourceLink(url,label){
  try{
    const x=new URL(url);
    if(x.protocol!=="https:"||!["apps.apple.com","play.google.com"].includes(x.hostname))return "";
    return '<a href="'+esc(x.href)+'" target="_blank" rel="noopener noreferrer">'+label+'</a>';
  }catch{return "";}
}
function detailHTML(g){
  const countries=[...new Set(g.variants.map(v=>v.country))].sort((a,b)=>a==="TW"?-1:b==="TW"?1:a.localeCompare(b));
  const detail=countries.map(country=>{
    const variants=g.variants.filter(v=>v.country===country).sort((a,b)=>a.platform.localeCompare(b.platform));
    return '<section class="detail-group"><h3>'+esc(twCountries[country]||country)+'</h3>'+
      variants.map(v=>'<div class="detail-row"><strong>'+esc(v.platform)+'｜'+esc(v.status)+'</strong>'+
      (v.date?'<p>上架／預約日期：'+esc(v.date)+'</p>':'')+
      (v.date_scope?'<p class="detail-note">日期依據：'+esc(v.date_scope)+'</p>':'')+
      (v.first_seen_at?'<p>系統最早發現：'+esc(v.first_seen_at.replace("T"," ").slice(0,16))+'（不等於正式上架時間）</p>':'')+
      (v.checked_at?'<p>最近核查：'+esc(v.checked_at.replace("T"," ").slice(0,16))+'</p>':'')+
      '<p>商店 ID：'+esc(v.id)+' · '+esc(v.source_kind||"商店公開資料")+'</p>'+
      sourceLink(v.source_url,'查看 '+v.store+' 官方商品頁')+'</div>').join('')+'</section>';
  }).join("");
  return '<p class="detail-summary">'+(g.developer?'開發商：'+esc(g.developer)+' · ':'')+
    '共於 '+countries.length+' 個國家或地區找到對應商品。'+
    (g.aliases?.length?'其他已知名稱：'+esc(g.aliases.join("、")):'')+'</p>'+detail+
    '<p class="detail-note">台灣優先顯示；「國際」可能包含不同的上市／預約狀態。App Store 產品發行日不保證就是各國首次上架日，版本更新日也不當作首發。</p>';
}
function openDetail(id){
  const game=model.games.find(g=>g.id===id);
  if(!game)return;
  $("dialog-title").textContent=game.name;
  $("dialog-body").innerHTML=detailHTML(game);
  const modal=$("detail-dialog");
  if(typeof modal.showModal==="function")modal.showModal();
  else modal.setAttribute("open","");
}
function render(){
  const results=filtered(),pages=Math.max(1,Math.ceil(results.length/model.perPage));
  model.page=Math.max(0,Math.min(model.page,pages-1));
  const visible=results.slice(model.page*model.perPage,(model.page+1)*model.perPage);
  const categoryTitle=model.query?"搜尋全部遊戲":model.category;
  $("result-title").textContent=categoryTitle+" · "+results.length+" 款";
  $("result-caption").textContent="每款遊戲只列一筆，台灣優先；平台與日期依各國官方商店證據呈現。";
  $("game-list").innerHTML=visible.length?visible.map(makeRow).join(""):
    '<div class="empty"><strong>沒有符合條件的遊戲</strong><div>'+
      (model.query?"請嘗試中文／英文名稱或商店 ID；搜尋沒有命中不表示商店沒有這款遊戲。":
      "可切換「全部遊戲」、台灣／國際或商店查看其他資料。")+
    '</div><button class="more" id="reset-filters" type="button">清除篩選</button></div>';
  for(const node of $("game-list").querySelectorAll("[data-detail]"))
    node.addEventListener("click",()=>openDetail(node.dataset.detail));
  const reset=$("reset-filters");
  if(reset)reset.addEventListener("click",()=>{
    model.category="全部遊戲";model.store="all";model.market="all";model.query="";model.page=0;
    $("game-search").value="";setSelected();render();
  });
  $("pagination").innerHTML=pages>1?
    '<button type="button" id="previous-page" '+(model.page===0?"disabled":"")+'>上一頁</button>'+
    '<span>第 '+(model.page+1)+' / '+pages+' 頁 · 每頁最多 '+model.perPage+' 款</span>'+
    '<button type="button" id="next-page" '+(model.page===pages-1?"disabled":"")+'>下一頁</button>':"";
  const prev=$("previous-page"),next=$("next-page");
  if(prev)prev.addEventListener("click",()=>{model.page--;render();$("results-heading").scrollIntoView({block:"start"})});
  if(next)next.addEventListener("click",()=>{model.page++;render();$("results-heading").scrollIntoView({block:"start"})});
}
function setSelected(){
  for(const b of root.querySelectorAll("[data-store]")){
    const selected=b.dataset.store===model.store;b.classList.toggle("active",selected);
    b.setAttribute("aria-pressed",String(selected));
  }
  for(const b of root.querySelectorAll("[data-category]")){
    const selected=b.dataset.category===model.category;b.classList.toggle("active",selected);
    b.setAttribute("aria-pressed",String(selected));
  }
  $("market-filter").value=model.market;
  $("game-order").value=model.sort;
}
function showHealth(){
  const h=model.health||{},s=model.summary||{};
  const checked=(h.updated_at||s.updated_at||"").replace("T"," ").slice(0,16);
  const succeeded=(h.sources||[]).filter(x=>x.state==="success").length;
  const total=(h.sources||[]).length;
  $("sync-state").textContent=checked?"上次收集："+checked+" UTC":"資料尚未更新";
  $("sync-detail").textContent=s.total_games?("已整理 "+s.total_games+" 款遊戲，"+s.total_store_variants+" 筆國別商店紀錄"):"";
  const failures=(h.errors||[]);
  $("health-description").textContent="本輪來源成功 "+succeeded+"/"+total+
    "；部分搜尋或商店可能受限，不能視為全球完整清單。";
  $("health-errors").innerHTML=failures.length?
    failures.slice(0,15).map(x=>'<li>'+esc(x.kind||"來源")+'：'+esc(x.error||"讀取失敗")+'</li>').join(""):
    '<li>目前沒有記錄到來源錯誤；不代表所有商店都已完整收錄。</li>';
  $("health-time").textContent="最後來源整理："+(h.updated_at||"尚無")+"｜只使用免費公開資料";
}
async function fetchJSON(path){
  const r=await fetch("/data/"+path+".json",{cache:"no-store"});
  if(!r.ok)throw new Error(path+" HTTP "+r.status);
  return r.json();
}
async function init(){
  root.querySelectorAll("[data-store]").forEach(b=>b.addEventListener("click",()=>{
    model.store=b.dataset.store;model.page=0;setSelected();render();
  }));
  root.querySelectorAll("[data-category]").forEach(b=>b.addEventListener("click",()=>{
    model.category=b.dataset.category;model.page=0;setSelected();render();
  }));
  $("market-filter").addEventListener("change",e=>{model.market=e.target.value;model.page=0;render()});
  $("game-order").addEventListener("change",e=>{model.sort=e.target.value;model.page=0;render()});
  $("game-search").addEventListener("input",e=>{model.query=e.target.value.trim();model.page=0;render()});
  $("search-clear").addEventListener("click",()=>{model.query="";$("game-search").value="";model.page=0;render()});
  $("dialog-close").addEventListener("click",()=>$("detail-dialog").close());
  $("detail-dialog").addEventListener("click",e=>{
    if(e.target===$("detail-dialog"))$("detail-dialog").close();
  });
  try{
    const [catalog,summary,health]=await Promise.all([fetchJSON("radar_catalog"),fetchJSON("radar_summary"),fetchJSON("radar_health")]);
    if(!Array.isArray(catalog.games))throw new Error("資料格式錯誤");
    model.games=catalog.games;model.health=health;model.summary=summary;
    setSelected();showHealth();render();
  }catch(error){
    $("sync-state").textContent="資料載入失敗";
    $("result-title").textContent="雷達資料尚未準備完成";
    $("game-list").innerHTML='<div class="empty"><strong>目前無法讀取正式遊戲清單</strong><div>'+
      esc(String(error.message||error))+'，請查看來源狀態；不會將來源失敗顯示成 0 款遊戲。</div></div>';
    $("health-description").textContent=String(error.message||error);
  }
}
if(root)root.addEventListener("DOMContentLoaded",init);
export {norm,normalizeQuery,searchMatches,selectedVariants,gameCategories,platformLines,filtered,detailHTML,model};
