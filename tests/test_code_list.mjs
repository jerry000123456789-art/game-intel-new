#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const a=html.indexOf('function renderCodes(){');
const b=html.indexOf("let selectedGuide",a);
assert(a>=0&&b>a,'redemption renderer is present');
const codeSection=html.slice(a,b);
let filteredHtml='',hiddenWrapper=false;
const dom={
  codeQ:{value:''},
  codeList:{
    get innerHTML(){return filteredHtml;},
    set innerHTML(value){filteredHtml=value;},
    querySelectorAll(){return [];}
  },
  codeLeads:{
    innerHTML:'',
    closest(){return {set hidden(v){hiddenWrapper=!!v;}}}
  },
};
const db={
  games:[{name:'沒有兌換碼的遊戲',first_seen_at:new Date().toISOString()}],
  codes:[
    {game:'原神',code:'TEST123456',discovered_at:'2026-11-08T00:00:00+00:00',source_url:'https://example.org/code'},
    {game:'崩壞：星穹鐵道',code:'ABCDEF12345',discovered_at:'2026-11-07T00:00:00+00:00',source_url:'https://example.org/code2'}
  ],
  leads:{codes:[{game:'沒有兌換碼的遊戲',title:'可能有兌換碼',source_url:'https://example.org/lead'}]}
};
const render=new Function('db','$','gameKey','safe','link','fmt','copy',
  codeSection+'\nreturn renderCodes;')(
    db,(id)=>dom[id],(name)=>String(name||'').toLowerCase(),
    x=>String(x),()=>'',x=>String(x),()=>{});
render();
assert(filteredHtml.includes('原神'));
assert(filteredHtml.includes('崩壞：星穹鐵道'));
assert(!filteredHtml.includes('沒有兌換碼的遊戲'));
assert(hiddenWrapper,'empty source section hidden');
assert(filteredHtml.indexOf('原神')<filteredHtml.indexOf('崩壞：星穹鐵道'),'newest code first');
dom.codeQ.value='不存在';
render();
assert(!filteredHtml.includes('原神'));
assert(filteredHtml.includes('目前沒有符合條件'));
console.log('PASS: only games with actual codes, newest first; no empty cards or leads-only games.');
