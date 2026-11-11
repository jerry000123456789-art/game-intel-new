#!/usr/bin/env node
/** Execute actual dashboard data loading with browser-like DOM stubs. */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const src=readFileSync(new URL('../business.js',import.meta.url),'utf8');
const elements=new Map(),errors=[];
function element(id){
  if(!elements.has(id)){
    const defaults={
      'gx-game-market':'all','gx-game-store':'all','gx-game-order':'new',
      'gx-code-order':'new','gx-content-kind':'all','gx-content-order':'new',
      'gx-studio-platform':'Facebook','gx-studio-angle':'useful',
    };
    elements.set(id,{
      id,value:defaults[id]||'',innerHTML:'',textContent:'',
      classList:{add(){},remove(){},toggle(){}},
      style:{},dataset:{},options:[{},{},{}],
      addEventListener(){},querySelectorAll(){return []},
      setAttribute(){},getAttribute(){return ''},
    });
  }
  return elements.get(id);
}
const storage=new Map();
const context={
  document:{
    getElementById:id=>element(id),
    querySelectorAll:()=>[],
    createElement:()=>({style:{},select(){},remove(){}}),
    body:{appendChild(){}},
    execCommand:()=>true
  },
  window:{scrollTo(){},isSecureContext:true,alert(){}},
  URL,Date,Intl,Number,String,JSON,Set,Map,Object,RegExp,encodeURIComponent,
  navigator:{clipboard:{writeText:async()=>{}}},
  localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,val)=>storage.set(key,val)},
  fetch:async pathname=>{
    const basename=new URL(pathname,'https://example.test').pathname.split('/').pop();
    const content=readFileSync(new URL('../data/'+basename,import.meta.url),'utf8');
    return {ok:true,json:async()=>JSON.parse(content)};
  },
  console:{log(){},warn(){},error:e=>errors.push(String(e))},
  setInterval:()=>1,setTimeout:()=>1
};
vm.runInNewContext(src,context,{filename:'business.js'});
await new Promise(resolve=>setTimeout(resolve,700));
assert.equal(elements.get('gx-sync-label').textContent,'資料已載入',errors.join('\n'));
assert.equal(errors.length,0,errors.join('\n'));
assert(elements.get('gx-game-list').innerHTML.includes('WellDiver'),
  'WellDiver should be visible in 30-day launch radar');
assert(elements.get('gx-code-list').innerHTML.includes('gx-code'),
  'Actual code data should render');
assert(elements.get('gx-content-list').innerHTML.includes('gx-feed-item'),
  'YouTube and news content should render');
assert(elements.get('gx-calendar-view').innerHTML.includes('gx-timeline-grid'),
  'Public event timeline should render without requiring watchlist selections');
assert(elements.get('gx-calendar-view').innerHTML.includes('金石禮帖'),
  'User-supplied Onmyoji event must appear in the public calendar');
assert(elements.get('gx-kpi-new').textContent!==''&&elements.get('gx-kpi-code').textContent!=='');
console.log('PASS: business dashboard actually loads current data, WellDiver, code cards, content and empty watchlist calendar');
