// Independent publisher Worker: X posting disabled until explicitly approved.
const send=(v,s=200)=>new Response(JSON.stringify(v),{status:s,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"}});
const err=(e,s=400)=>send({ok:false,error:e},s);
const now=()=>new Date().toISOString();
const approved=e=>e.X_PUBLISH_ENABLED==="true"&&["X_API_KEY","X_API_SECRET","X_ACCESS_TOKEN","X_ACCESS_TOKEN_SECRET"].every(k=>!!e[k]);
const adminReady=e=>typeof e.ADMIN_API_TOKEN==="string"&&e.ADMIN_API_TOKEN.length>=32;
const enc=s=>encodeURIComponent(String(s)).replace(/[!'()*]/g,c=>"%"+c.charCodeAt(0).toString(16).toUpperCase());
async function permitted(req,e){
  if(!adminReady(e))return false;
  const match=/^Bearer\s+(\S+)$/i.exec(req.headers.get("authorization")||"");
  if(!match)return false;
  const digest=async s=>new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s)));
  const [a,b]=await Promise.all([digest(match[1]),digest(e.ADMIN_API_TOKEN)]);
  let difference=0;for(let i=0;i<a.length;i++)difference|=a[i]^b[i];
  return difference===0;
}
function validJob(v){
  if(!v||typeof v!=="object"||Array.isArray(v))throw Error("invalid_job");
  const platform=String(v.platform||"").toLowerCase(),title=String(v.title||"").trim(),body=String(v.body||"").trim(),raw=String(v.scheduled_at||"");
  if(!["x","pixnet","bahamut"].includes(platform))throw Error("unsupported_platform");
  if(!title||title.length>128)throw Error("invalid_title");
  if(!body||body.length>12000)throw Error("invalid_body");
  if(platform==="x"&&[...body].length>260)throw Error("x_post_too_long");
  if(!/(?:Z|[+-]\d\d:\d\d)$/.test(raw))throw Error("timezone_required");
  const d=new Date(raw);
  if(!Number.isFinite(d.getTime())||d.getTime()<Date.now()-300000||d.getTime()>Date.now()+365*86400000)throw Error("invalid_schedule");
  return {platform,title,body,scheduled_at:d.toISOString()};
}
async function publishX(text,e){
  if(!approved(e))return {ok:false,error:"x_not_authorized"};
  const url="https://api.x.com/2/tweets";
  const values={oauth_consumer_key:e.X_API_KEY,oauth_nonce:crypto.randomUUID().replaceAll("-",""),oauth_signature_method:"HMAC-SHA1",oauth_timestamp:String(Math.floor(Date.now()/1000)),oauth_token:e.X_ACCESS_TOKEN,oauth_version:"1.0"};
  const sorted=Object.entries(values).map(([a,b])=>[enc(a),enc(b)]).sort((a,b)=>a[0].localeCompare(b[0])||a[1].localeCompare(b[1]));
  const base=["POST",enc(url),enc(sorted.map(x=>x.join("=")).join("&"))].join("&");
  const key=await crypto.subtle.importKey("raw",new TextEncoder().encode(enc(e.X_API_SECRET)+"&"+enc(e.X_ACCESS_TOKEN_SECRET)),{name:"HMAC",hash:"SHA-1"},false,["sign"]);
  const bytes=new Uint8Array(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(base)));
  const signature=btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(""));
  const auth="OAuth "+Object.entries({...values,oauth_signature:signature}).map(([a,b])=>enc(a)+'="'+enc(b)+'"').join(", ");
  const response=await fetch(url,{method:"POST",headers:{authorization:auth,"content-type":"application/json"},body:JSON.stringify({text})});
  let json={};try{json=await response.json()}catch{}
  if(!response.ok)return {ok:false,error:"x_http_"+response.status};
  const id=json?.data?.id;
  if(!id||!/^\d{5,25}$/.test(String(id)))return {ok:false,error:"x_confirmation_missing"};
  return {ok:true,id:String(id),url:"https://x.com/Cat577sietc/status/"+id};
}
const PAGE='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>電玩喵發文管理</title><style>:root{font-family:system-ui,sans-serif;line-height:1.5;background:#eaeaef;color:#2d3142}body{max-width:840px;margin:24px auto;padding:16px}main,section{background:white;border-radius:12px;padding:22px;margin:15px 0}input,select,textarea{box-sizing:border-box;width:100%;padding:10px;border:1px solid #abb0bd;border-radius:8px;margin:7px 0 14px;font:inherit}textarea{min-height:140px}button{background:#18574f;color:white;border:0;border-radius:7px;padding:10px 18px;cursor:pointer}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;text-align:left;padding:8px}div.scroll{overflow:auto}</style><h1>電玩喵｜文章排程</h1><p>X 自動發布預設停用，痞客邦與巴哈姆特目前僅保存草稿。</p><main><label>管理 Token（本頁暫存）</label><input id="token" type="password" autocomplete="off"><button id="load">查看文章</button><p id="health"></p></main><section><h2>新增文章</h2><form id="form"><label>平台</label><select name="platform"><option value="x">X</option><option value="pixnet">痞客邦（草稿）</option><option value="bahamut">巴哈姆特（草稿）</option></select><label>標題</label><input name="title" required maxlength="128"><label>內容</label><textarea name="body" required></textarea><label>發布時間（本地時區）</label><input type="datetime-local" name="when" required><button>儲存排程</button></form><p id="message"></p></section><section><h2>文章紀錄</h2><div class="scroll"><table><thead><tr><th>平台</th><th>標題</th><th>時間</th><th>狀態</th><th>網址</th></tr></thead><tbody id="jobs"></tbody></table></div></section><script>let token="";const $=id=>document.getElementById(id);const msg=s=>$("message").textContent=s;async function api(path,method="GET",obj){const r=await fetch("/api"+path,{method,headers:{authorization:"Bearer "+token,"content-type":"application/json"},body:obj?JSON.stringify(obj):undefined});let data=await r.json();if(!r.ok)throw Error(data.error||r.status);return data}async function load(){token=$("token").value.trim();try{let [h,d]=await Promise.all([api("/health"),api("/jobs")]);$("health").textContent=h.auto_x_enabled?"X 發布已啟用":"X 發布未啟用";$("jobs").replaceChildren();for(let j of d.jobs){let tr=document.createElement("tr");for(let s of [j.platform,j.title,new Date(j.scheduled_at).toLocaleString("zh-TW"),j.status]){let td=document.createElement("td");td.textContent=s;tr.append(td)}let td=document.createElement("td");if(j.external_url){let a=document.createElement("a");a.textContent="文章連結";a.href=j.external_url;a.target="_blank";a.rel="noopener noreferrer";td.append(a)}else td.textContent=j.error_code||"—";tr.append(td);$("jobs").append(tr)}}catch(e){msg(e.message)}}$("load").onclick=load;$("form").onsubmit=async e=>{e.preventDefault();token=$("token").value.trim();let f=new FormData(e.target);try{let result=await api("/jobs","POST",{platform:f.get("platform"),title:f.get("title"),body:f.get("body"),scheduled_at:new Date(f.get("when")).toISOString()});msg("已儲存："+result.job.status);await load()}catch(e){msg("無法儲存："+e.message)}};</script></html>';
export class PublisherQueue{
  constructor(ctx,env){
    this.ctx=ctx;this.env=env;
    ctx.blockConcurrencyWhile(async()=>{
      ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,platform TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,scheduled_at TEXT NOT NULL,status TEXT NOT NULL,external_id TEXT,external_url TEXT,error_code TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)");
      ctx.storage.sql.exec("CREATE INDEX IF NOT EXISTS jobs_due_idx ON jobs(status,scheduled_at)");
    });
  }
  async fetch(req){
    const sql=this.ctx.storage.sql,path=new URL(req.url).pathname;
    try{
      if(req.method==="GET"&&path==="/health")return send({ok:true,auto_x_enabled:approved(this.env)});
      if(req.method==="GET"&&path==="/jobs")return send({ok:true,jobs:sql.exec("SELECT id,platform,title,scheduled_at,status,external_url,error_code FROM jobs ORDER BY created_at DESC LIMIT 100").toArray()});
      if(req.method==="POST"&&path==="/jobs"){
        const j=validJob(await req.json()),id=crypto.randomUUID(),date=now();
        const status=j.platform==="x"?(approved(this.env)?"queued":"blocked_setup"):"manual_required";
        sql.exec("INSERT INTO jobs(id,platform,title,body,scheduled_at,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",id,j.platform,j.title,j.body,j.scheduled_at,status,date,date);
        return send({ok:true,job:{id,...j,status}},201);
      }
      const activate=/^\/jobs\/([\da-f-]{36})\/activate$/.exec(path);
      if(req.method==="POST"&&activate){
        if(!approved(this.env))return err("x_not_approved",409);
        sql.exec("UPDATE jobs SET status='queued',updated_at=? WHERE id=? AND platform='x' AND status='blocked_setup'",now(),activate[1]);
        return send({ok:sql.exec("SELECT changes() AS n").one().n===1});
      }
      if(req.method==="POST"&&path==="/tick"){
        const due=sql.exec("SELECT id,platform,body FROM jobs WHERE status='queued' AND scheduled_at<=? ORDER BY scheduled_at LIMIT 10",now()).toArray();
        let processed=0;
        for(const j of due){
          sql.exec("UPDATE jobs SET status='publishing',updated_at=? WHERE id=? AND status='queued'",now(),j.id);
          if(sql.exec("SELECT changes() AS n").one().n!==1)continue;
          let result;
          try{result=j.platform==="x"&&approved(this.env)?await publishX(j.body,this.env):{ok:false,error:"not_configured"}}catch{result={ok:false,error:"network_uncertain"}}
          if(result.ok)sql.exec("UPDATE jobs SET status='published',external_id=?,external_url=?,error_code=NULL,updated_at=? WHERE id=?",result.id,result.url,now(),j.id);
          else sql.exec("UPDATE jobs SET status='needs_review',error_code=?,updated_at=? WHERE id=?",result.error,now(),j.id);
          processed++;
        }
        return send({ok:true,processed});
      }
      return err("not_found",404);
    }catch(e){
      const allowed=["invalid_job","unsupported_platform","invalid_title","invalid_body","x_post_too_long","timezone_required","invalid_schedule"];
      return err(allowed.includes(e.message)?e.message:"internal_error",allowed.includes(e.message)?400:500);
    }
  }
}
const stub=e=>e.PUBLISHER.get(e.PUBLISHER.idFromName("dianwanmiao-main"));
export default {
  async fetch(req,env){
    const url=new URL(req.url);
    if(req.method==="GET"&&url.pathname==="/")return new Response(PAGE,{headers:{"content-type":"text/html; charset=utf-8","content-security-policy":"default-src 'none'; connect-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'","cache-control":"no-store","x-content-type-options":"nosniff"}});
    if(!url.pathname.startsWith("/api/"))return err("not_found",404);
    if(!adminReady(env))return err("admin_not_configured",503);
    if(!(await permitted(req,env)))return err("unauthorized",401);
    if(!env.PUBLISHER)return err("storage_not_configured",503);
    return stub(env).fetch(new Request("https://publisher.internal"+url.pathname.slice(4),{method:req.method,headers:{"content-type":"application/json"},body:req.method==="GET"?undefined:req.body,duplex:req.method==="GET"?undefined:"half"}));
  },
  async scheduled(event,env,ctx){
    if(!adminReady(env)||!env.PUBLISHER)return;
    ctx.waitUntil(stub(env).fetch(new Request("https://publisher.internal/tick",{method:"POST"})));
  }
};