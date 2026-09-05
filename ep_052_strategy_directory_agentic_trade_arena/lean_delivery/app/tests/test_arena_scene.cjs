// VERSION HISTORY v1.1.0 · 2026-09-02 · Exercise automatic sign-in polling, presence changes, pause and sign-out.
// v1.0.1 · 2026-09-02 · Verify a single available booth is centred after browser review.
// v1.0.0 · 2026-09-02 · Exercise actual browser projection and renderer event logic without a synthetic trading engine.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),test=require('node:test'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/lean_exchange/web/arena.js'),'utf8');
const context={window:{}};vm.createContext(context);vm.runInContext(source.split("(()=>{'use strict';")[0],context);
const projection=context.window.ArenaProjection;
const rows=[{strategy_id:'DNA_1',status:'active',price:{unit_price:'1.5000000000'},available_units:550,issued_units:1000,valuation_bound:true,available_to_buy:true},{strategy_id:'DNA_2',status:'active',price:null,available_units:null,issued_units:null,valuation_bound:false,available_to_buy:false},{strategy_id:'DNA_3',status:'active',price:{unit_price:'0.0000000000'},available_units:0,issued_units:10,valuation_bound:true,available_to_buy:false}];
test('catalogue keeps unknown and sold-out explicit; available view excludes both',()=>{const all=projection.booths(rows,'all','',0,24);assert.equal(all.total,3);assert.equal(all.items[0].priceText,'1.5');assert.equal(all.items[1].priceText,null);assert.equal(all.items[1].availabilityLabel,'AWAITING VALUATION');assert.equal(all.items[2].priceText,'0');assert.equal(all.items[2].availabilityLabel,'SOLD OUT');const available=projection.booths(rows,'available','',0,24);assert.equal(available.total,1);assert.equal(available.items[0].id,'DNA_1');});
test('search and pagination clamp without removing source records',()=>{assert.equal(projection.booths(rows,'all','dna_2',9,1).items[0].id,'DNA_2');assert.equal(projection.booths(rows,'all','missing',0,6).total,0);assert.equal(rows.length,3);});
test('one available booth is centred',()=>{const floor=Object.create(context.window.ArenaFloor.prototype);floor.bots=new Map();floor.update({agents:[],instruments:projection.booths(rows,'available','',0,24).items,events:[],eventId:0});assert.equal(floor.positions[0].x,0);assert.equal(floor.positions[0].z,-6);});
test('UUID agents are positioned finitely and only new recorded events move them',()=>{const floor=Object.create(context.window.ArenaFloor.prototype);floor.bots=new Map();floor.lastEvent=0;const id='2e3c683e-4cef-4a70-afa8-b7811405c63d';const data={agents:[{id}],instruments:projection.booths(rows,'all','',0,24).items,events:[{id:10,agent:id,type:'QUERY'}],eventId:10};floor.update(data,false);const bot=floor.bots.get(id);assert.ok(Number.isFinite(bot.x));assert.equal(bot.tz,10);floor.update({...data,events:[...data.events,{id:11,agent:id,type:'QUERY'}],eventId:11},true);assert.equal(bot.tx,0);assert.equal(bot.tz,1.5);floor.update({...data,events:[{id:12,agent:id,type:'BUY',instrument:'DNA_1'}],eventId:12},true);assert.equal(bot.tx,floor.positions[0].x+1.8);floor.update({...data,agents:[],eventId:12},true);assert.equal(floor.bots.size,0);});
test('observer contains no trading engine, fake return haze, browser storage or mutation calls',()=>{for(const forbidden of ['localStorage','sessionStorage','.innerHTML','performanceHaze','Math.random','engine.js',"method:'POST'","method:'DELETE'",'$0.0001'])assert.ok(!source.includes(forbidden),forbidden);});

test('sign-in automatically polls connected agents; pause and sign-out cancel polling',async()=>{
 const elements=new Map(),timers=new Map();let timerId=0,agents=[],floor;
 const element=()=>({value:'',textContent:'',hidden:false,clientWidth:800,classList:{toggle(){}},append(){},replaceChildren(){},setAttribute(){},querySelectorAll(){return[];},reset(){}});
 const get=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
 class FloorStub{constructor(){floor=this;this.bots=new Map();}update(data){this.data=data;}resize(){}}
 const sandbox={ArenaFloor:FloorStub,ArenaProjection:projection,URLSearchParams,Map,Set,Date,String,window:{addEventListener(){}},document:{getElementById:get,createElement:element},setTimeout(fn,ms){const id=++timerId;timers.set(id,{fn,ms});return id;},clearTimeout(id){timers.delete(id);},async fetch(url){let data={};if(url==='/v1/exchange')data={instance_id:'test',configuration:{view_poll_seconds:5,activity_page_size:100}};else if(url==='/v1/arena/connections')data={items:agents};else if(url.startsWith('/v1/strategies'))data={items:[]};else if(url.startsWith('/v1/arena/activity'))data={items:[],next_cursor:0,has_more:false};return{ok:true,json:async()=>data};}};
 vm.createContext(sandbox);vm.runInContext("(()=>{'use strict';"+source.split("(()=>{'use strict';")[1],sandbox);
 get('arena-token').value='test-only';await get('arena-access').onsubmit({preventDefault(){},submitter:{}});
 assert.equal(get('arena-live').textContent,'Stop live updates');assert.equal(timers.size,1);
 async function poll(){const [id,timer]=timers.entries().next().value;assert.equal(timer.ms,5000);timers.delete(id);await timer.fn();}
 agents=[{agent_id:'external-agent',last_seen:1}];await poll();assert.equal(get('floor-agent-count').textContent,'1');assert.equal(floor.data.agents[0].id,'external-agent');
 agents=[];await poll();assert.equal(get('floor-agent-count').textContent,'0');assert.equal(floor.data.agents.length,0);
 get('arena-live').onclick();assert.equal(timers.size,0);assert.equal(get('arena-live').textContent,'Start live updates');
 get('arena-signout').onclick();assert.equal(timers.size,0);assert.equal(get('arena-workspace').hidden,true);assert.equal(floor.data.agents.length,0);
});
