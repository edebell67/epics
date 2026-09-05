/* Perspective-projected 3D geometry, rendered locally without external libraries.
 * VERSION HISTORY
 * v2.0.2 · 2026-09-02 · Centre a single available booth instead of reserving an empty second column.
 * v2.0.1 · 2026-09-02 · Spread small booth pages across the floor to keep narrow-screen labels readable.
 * v2.0.0 · 2026-09-02 · Reuse original perspective geometry with API-only data; no simulation data, fake returns or synthetic history.
 * v1.1.0 · 2026-08-28 · Adds return-based green/red agent haze; existing renderer predates this history.
 */
(function(){'use strict';
const MINT='#b5f5d2',AMBER='#f3b478',BLUE='#8dc8e9';
class ArenaFloor{
 constructor(canvas,data,onSelect){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.data=data;this.onSelect=onSelect;this.yaw=-.36;this.pitch=.76;this.zoom=1;this.auto=false;this.paused=false;this.selected=null;this.hits=[];this.bots=new Map();this.lastEvent=0;this.time=0;this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;this.positions=[];this.resize();this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(canvas);this.bind();this.last=performance.now();this.frame=this.frame.bind(this);requestAnimationFrame(this.frame);}
 resize(){const r=this.canvas.getBoundingClientRect();this.w=r.width;this.h=r.height;const d=Math.min(window.devicePixelRatio||1,2);this.canvas.width=this.w*d;this.canvas.height=this.h*d;this.ctx.setTransform(d,0,0,d,0,0);}
 project(x,y,z){const u=x*Math.cos(this.yaw)-z*Math.sin(this.yaw),d=x*Math.sin(this.yaw)+z*Math.cos(this.yaw),v=y*Math.cos(this.pitch)-d*Math.sin(this.pitch),depth=y*Math.sin(this.pitch)+d*Math.cos(this.pitch);const scale=Math.min(this.w/40,this.h/28)*this.zoom*48/(48-depth);return{x:this.w*.5+u*scale,y:this.h*.44-v*scale,depth,scale};}
 bind(){let down=null;this.canvas.addEventListener('pointerdown',e=>{down={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY};this.canvas.setPointerCapture(e.pointerId)});this.canvas.addEventListener('pointermove',e=>{const r=this.canvas.getBoundingClientRect();if(down){this.yaw+=(e.clientX-down.x)*.007;this.pitch=Math.max(.3,Math.min(1.28,this.pitch+(e.clientY-down.y)*.004));down.x=e.clientX;down.y=e.clientY;}else{const hit=this.hit(e.clientX-r.left,e.clientY-r.top);this.canvas.style.cursor=hit?'pointer':'grab';}});this.canvas.addEventListener('pointerup',e=>{if(down&&Math.hypot(e.clientX-down.startX,e.clientY-down.startY)<6){const r=this.canvas.getBoundingClientRect(),hit=this.hit(e.clientX-r.left,e.clientY-r.top);if(hit){this.selected=hit.id;this.onSelect(hit.kind,hit.id);}}down=null;});this.canvas.addEventListener('pointercancel',()=>down=null);this.canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.65,Math.min(2,this.zoom-e.deltaY*.001))},{passive:false});this.canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','='].includes(e.key)){e.preventDefault();if(e.key==='ArrowLeft')this.yaw-=.1;if(e.key==='ArrowRight')this.yaw+=.1;if(e.key==='ArrowUp')this.pitch=Math.min(1.28,this.pitch+.08);if(e.key==='ArrowDown')this.pitch=Math.max(.3,this.pitch-.08);if(e.key==='+'||e.key==='=')this.zoom=Math.min(2,this.zoom+.1);if(e.key==='-')this.zoom=Math.max(.65,this.zoom-.1);}});}
 hit(x,y){return[...this.hits].reverse().find(h=>x>=h.x&&x<=h.x+h.w&&y>=h.y&&y<=h.y+h.h);}
 poly(points,fill,stroke=null,width=1){const c=this.ctx;c.beginPath();points.forEach((p,i)=>{const q=this.project(...p);i?c.lineTo(q.x,q.y):c.moveTo(q.x,q.y)});c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}}
 line(points,color,width=1,dash=[]){const c=this.ctx;c.beginPath();points.forEach((p,i)=>{const q=this.project(...p);i?c.lineTo(q.x,q.y):c.moveTo(q.x,q.y)});c.strokeStyle=color;c.lineWidth=width;c.setLineDash(dash);c.stroke();c.setLineDash([]);}
 box(queue,x,y,z,w,h,d,colors,stroke='#35515c'){const p=[[x-w/2,y,z-d/2],[x+w/2,y,z-d/2],[x+w/2,y,z+d/2],[x-w/2,y,z+d/2],[x-w/2,y+h,z-d/2],[x+w/2,y+h,z-d/2],[x+w/2,y+h,z+d/2],[x-w/2,y+h,z+d/2]];const faces=[[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7],[4,5,6,7]];faces.forEach((f,i)=>{const points=f.map(k=>p[k]);const depth=points.reduce((a,v)=>a+this.project(...v).depth,0)/4;queue.push({depth,draw:()=>this.poly(points,colors[i%colors.length],stroke,.6)});});}
 prism(queue,x,y,z,r,h,colors,stroke='#35515c'){const bottom=Array.from({length:8},(_,i)=>[x+Math.cos(Math.PI/8+i*Math.PI/4)*r,y,z+Math.sin(Math.PI/8+i*Math.PI/4)*r]),top=bottom.map(([px,,pz])=>[px,y+h,pz]);for(let i=0;i<8;i++){const face=[bottom[i],bottom[(i+1)%8],top[(i+1)%8],top[i]],depth=face.reduce((sum,v)=>sum+this.project(...v).depth,0)/4;queue.push({depth,draw:()=>this.poly(face,colors[i%colors.length],stroke,.6)});}const depth=top.reduce((sum,v)=>sum+this.project(...v).depth,0)/8;queue.push({depth,draw:()=>this.poly(top,colors[colors.length-1],stroke,.7)});}
 update(data,animate=false){this.data=data;const n=data.instruments.length,cols=Math.min(Math.max(1,n),6,Math.max(1,Math.ceil(Math.sqrt(n*1.5)))),rows=Math.ceil(n/cols);this.positions=data.instruments.map((_,i)=>({x:cols===1?0:-14+(i%cols)*28/(cols-1),z:rows===1?-6:-8+Math.floor(i/cols)*14/(rows-1)}));if(!animate)this.lastEvent=data.eventId;this.sync();}
 sync(){const active=new Set(this.data.agents.map(a=>a.id));for(const id of this.bots.keys())if(!active.has(id))this.bots.delete(id);
 for(const a of this.data.agents){if(!this.bots.has(a.id)){const n=[...a.id].reduce((v,c)=>(v*31+c.charCodeAt(0))>>>0,0);this.bots.set(a.id,{id:a.id,x:-17+(n%34),z:10,tx:-17+(n%34),tz:10,color:MINT,pulse:0});}}
 for(const e of this.data.events.filter(e=>e.id>this.lastEvent)){const bot=this.bots.get(e.agent);if(!bot)continue;if(e.type==='QUERY'){bot.tx=0;bot.tz=1.5;bot.color=BLUE;bot.pulse=1;}else if(e.type==='BUY'||e.type==='SELL'){const i=this.data.instruments.findIndex(x=>x.id===e.instrument);if(i>=0){bot.tx=this.positions[i].x+1.8;bot.tz=this.positions[i].z+1.8;bot.color=e.type==='SELL'?AMBER:MINT;bot.pulse=1;}}}
 this.lastEvent=this.data.eventId;
 }
 label(text,x,y,z,color,size=10,align='center'){const p=this.project(x,y,z),c=this.ctx;c.font=`${size}px Consolas, monospace`;c.textAlign=align;c.fillStyle=color;c.fillText(text,p.x,p.y);}
 ground(){const c=this.ctx;this.poly([[-19,-.6,-14],[19,-.6,-14],[19,-.6,14],[-19,-.6,14]],'#071015','#354853');this.poly([[-19,0,-14],[19,0,-14],[19,0,14],[-19,0,14]],'#15262e','#3c5866');this.poly([[-19,0,14],[19,0,14],[19,-.6,14],[-19,-.6,14]],'#101c24','#304853');
 for(let x=-18;x<=18;x+=2)this.line([[x,.01,-14],[x,.01,14]],'#263c46',.45);for(let z=-14;z<=14;z+=2)this.line([[-19,.01,z],[19,.01,z]],'#263c46',.45);
 this.line([[-18,.03,-13],[18,.03,-13],[18,.03,13],[-18,.03,13],[-18,.03,-13]],'#5e8d80',1);
 for(const z of [-4,4]){this.line([[-18,.03,z],[18,.03,z]],'#597d8670',1,[4,7]);}
 this.line([[-19,.04,11],[-15,.04,11]],MINT,3);this.line([[15,.04,11],[19,.04,11]],AMBER,3);
 this.label('ENTRY',-17.1,.1,12.8,'#b5f5d2',8);this.label('EXIT',17,.1,12.8,'#f3b478',8);
 const p=this.project(0,.05,12.5);c.save();c.translate(p.x,p.y);c.fillStyle='#688b9850';c.font='bold 17px Bahnschrift, sans-serif';c.textAlign='center';c.fillText('A G E N T I C   E X C H A N G E',0,0);c.restore();
 }
 drawBooth(queue,x,i){const p=this.positions[i],color=x.availableToBuy?MINT:'#708996';const isSelected=this.selected===x.id;this.box(queue,p.x,.05,p.z,4,.28,3.4,['#1a2d36','#1a3038','#263c42','#192c33','#263d43']);this.box(queue,p.x,.34,p.z,3.35,.65,2.6,['#243e47','#192d36','#2c444c','#1c323a','#35515b']);this.box(queue,p.x,.98,p.z,3.6,.14,2.85,['#365a62','#2d454c','#344d50','#233d45',isSelected?'#74a890':'#416363']);this.box(queue,p.x,1.12,p.z-.55,2.8,1.35,.20,['#0b1b20','#23404a','#101e25','#263d48','#345460']);this.box(queue,p.x,1.13,p.z+.85,2.2,.45,.12,['#0b1b20','#26424d','#132a30','#23414a','#39626a']);
 const panel=[[p.x-1.22,1.28,p.z-.43],[p.x+1.22,1.28,p.z-.43],[p.x+1.22,2.32,p.z-.43],[p.x-1.22,2.32,p.z-.43]];queue.push({depth:this.project(p.x,1.8,p.z-.42).depth+.1,draw:()=>{this.poly(panel,'#102a28',color,.6);this.label(x.priceText===null?'NO QUOTE':'USD '+x.priceText,p.x,1.85,p.z-.42,color,7);}});
 this.box(queue,p.x,.22,p.z+1.7,2.7,.04,.06,[color],color);
 // Tall corner supports create the silhouette of a physical exchange booth.
 for(const offset of [-1.55,1.55])this.box(queue,p.x+offset,.32,p.z-.9,.09,2.5,.09,['#426571','#304b56']);
 this.box(queue,p.x,2.8,p.z-.9,3.3,.13,.2,['#4a6a73','#314e59','#567985','#2b4650','#6c9995']);
 }
 boothLabel(x,i){const p=this.positions[i],q=this.project(p.x,3.45,p.z),c=this.ctx,w=this.w<540?96:116,h=44,left=q.x-w/2,top=q.y-h,color=x.availableToBuy?MINT:'#8aabb8';c.fillStyle=this.selected===x.id?'#203c30f5':'#0c1a20ee';c.strokeStyle=this.selected===x.id?MINT:'#38545d';c.lineWidth=1;c.beginPath();c.roundRect(left,top,w,h,3);c.fill();c.stroke();c.textAlign='left';c.font='10px Bahnschrift,sans-serif';c.fillStyle='#dfebe9';c.fillText(x.id,left+7,top+13);c.font='9px Consolas,monospace';c.fillStyle=color;c.fillText(x.priceText===null?'UNPRICED':'USD '+x.priceText,left+7,top+26);c.font='8px Consolas,monospace';c.fillText(x.availabilityLabel,left+7,top+38);this.hits.push({kind:'strategy',id:x.id,x:left,y:top,w,h});}
 frame(now){const dt=Math.min((now-this.last)/1000,.05);this.last=now;this.time+=dt;if(!this.w||!this.h||document.hidden){requestAnimationFrame(this.frame);return;}this.sync();if(this.auto&&!this.reduced)this.yaw+=dt*.07;const c=this.ctx;c.clearRect(0,0,this.w,this.h);this.hits=[];this.ground();const queue=[];
 // Intelligence kiosk, used by agents paying for a query.
 this.box(queue,0,.1,0,2,.35,2,['#1a3547','#112c3a','#1e3c4e','#172d3a','#315467']);this.box(queue,0,.45,0,1,2.6,1,['#204256','#1c3648','#2c5265','#162f3d','#7dabbd'],BLUE);
 this.data.instruments.forEach((x,i)=>this.drawBooth(queue,x,i));
 for(const [id,b] of this.bots){const dx=b.tx-b.x,dz=b.tz-b.z,d=Math.hypot(dx,dz);if(!this.paused){if(this.reduced){b.x=b.tx;b.z=b.tz;}else if(d>.08){const v=Math.min(d,dt*3.4);b.x+=dx/d*v;b.z+=dz/d*v;}b.pulse=Math.max(0,b.pulse-dt*.14);}
 const q=this.project(b.x,0,b.z);if(b.pulse>.2&&d>.8){this.line([[b.x,.09,b.z],[b.tx,.09,b.tz]],b.color+'40',1,[2,5]);}c.fillStyle='#050b1090';c.beginPath();c.ellipse(q.x,q.y,q.scale*.33,q.scale*.15,0,0,Math.PI*2);c.fill();const bob=!this.reduced&&d>.1&&!this.paused?Math.sin(this.time*12+q.x)*.035:0;this.box(queue,b.x,.08+bob,b.z,.32,.53,.25,['#365569','#2b4656',b.color,'#365566','#8eafbd'],'#496371');this.box(queue,b.x,.66+bob,b.z,.27,.25,.25,[b.color,'#476372',b.color,'#476372',b.color],'#486873');const head=this.project(b.x,1,b.z);this.hits.push({kind:'agent',id,x:head.x-7,y:head.y-3,w:14,h:23});if(this.selected===id){c.strokeStyle=MINT;c.lineWidth=1.5;c.beginPath();c.ellipse(q.x,q.y,q.scale*.65,q.scale*.3,0,0,Math.PI*2);c.stroke();}
 }
 queue.sort((a,b)=>a.depth-b.depth);for(const item of queue)item.draw();
 this.data.instruments.map((x,i)=>({x,i,depth:this.project(this.positions[i].x,3,this.positions[i].z).depth})).sort((a,b)=>a.depth-b.depth).forEach(({x,i})=>this.boothLabel(x,i));
 this.label('INTELLIGENCE',0,3.6,0,BLUE,this.w<540?6:8);this.label('USD '+this.data.queryFee+' / DELIVERY',0,3.05,0,'#7799ae',this.w<540?5:6);
 requestAnimationFrame(this.frame);}
}
window.ArenaFloor=ArenaFloor;
})();



window.ArenaProjection={
 amount(value){return value===null||value===undefined?null:String(value).replace(/(\.\d*?[1-9])0+$|\.0+$/,'$1');},
 booths(items,mode,search,page,size){const term=search.toLowerCase();const filtered=items.filter(x=>(mode!=='available'||x.available_to_buy===true)&&(x.strategy_id+' '+(x.descriptive_name||'')).toLowerCase().includes(term)).sort((a,b)=>a.strategy_id.localeCompare(b.strategy_id));const pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.min(Math.max(0,page),pages-1);return{page,pages,total:filtered.length,items:filtered.slice(page*size,(page+1)*size).map(x=>({id:x.strategy_id,name:x.descriptive_name||x.strategy_id,priceText:this.amount(x.price?.unit_price),availableToBuy:x.available_to_buy===true,availabilityLabel:!x.valuation_bound?'AWAITING VALUATION':x.available_units===0?'SOLD OUT':x.status!=='active'?'NOT ACTIVE':x.available_units+' UNITS AVAILABLE',record:x}))};}
};
// VERSION HISTORY v2.0.3 · 2026-09-02 · Start presence polling on sign-in; invalidate paused polling loops.
// v2.0.0 · 2026-09-02 · Connect reused 3D geometry to read-only API snapshots; retain audit controls and isolate credentials.
// v1.0.1 · 2026-09-02 · Ignore old live-refresh completions after sign-out and use singular event labels.
// v1.0.0 · 2026-09-02 · Read-only Arena with instance-scoped cursors, dynamic collections and memory-only authentication.
(()=>{'use strict';
const $=id=>document.getElementById(id),node=(tag,value,cls)=>{const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n;};
let catalogue=[],connected=[],configuration={},floorPage=0,floorInstance='',selected=null;
let token='',session=0,requestVersion=0,cursor=0,instance='',events=[],filters=new URLSearchParams(),timer=null,live=false,liveVersion=0,pollSeconds=5;

const floor=new ArenaFloor($('arena-canvas'),{agents:[],instruments:[],events:[],eventId:0,queryFee:'—'},inspect);
function pair(dl,key,value){dl.append(node('dt',key),node('dd',value===null||value===undefined?'Not available':String(value)));}
function inspect(kind,id){selected={kind,id};floor.selected=id;$('floor-inspector').replaceChildren();$('inspect-title').textContent=id;
 const dl=node('dl','');
 if(kind==='strategy'){const x=catalogue.find(x=>x.strategy_id===id);if(!x)return;pair(dl,'Strategy',x.descriptive_name||id);pair(dl,'Current unit price',x.price?'USD '+x.price.unit_price:'Unpriced — no published valuation');pair(dl,'Available units',x.available_units);pair(dl,'Issued units',x.issued_units);pair(dl,'Available to buy',x.available_to_buy?'Yes':'No');pair(dl,'Source status',x.status);pair(dl,'Price version',x.price?.price_version);pair(dl,'Provenance',x.price?.provenance);}
 else if(kind==='agent'){const x=connected.find(x=>x.agent_id===id);pair(dl,'Presence',x?'Connected':'Not currently connected');if(x)pair(dl,'Last seen',new Date(x.last_seen*1000).toLocaleString());pair(dl,'Private positions','Available only in the participant workspace');}
 else {const x=events.find(x=>x.event_id===id);if(!x)return;$('inspect-title').textContent=x.operation+' · event '+x.cursor;$('floor-inspector').append(node('pre',JSON.stringify(x,null,2)));return;}
 $('floor-inspector').append(dl);
}
function renderFloor(animate=false){const size=$('arena-canvas').clientWidth<540?6:24;const view=ArenaProjection.booths(catalogue,$('floor-availability').value,$('floor-search').value,floorPage,size);floorPage=view.page;
 floor.update({agents:connected.map(a=>({id:a.agent_id})),instruments:view.items,events:events.map(e=>({id:e.cursor,agent:e.agent_id,type:e.operation,instrument:e.strategy_id})),eventId:cursor,queryFee:ArenaProjection.amount(configuration.intelligence_fee)||'—'},animate);
 $('floor-agent-count').textContent=String(connected.length);$('floor-page').textContent=(view.total?floorPage+1:0)+' / '+view.pages+' · '+view.total+' strategies';$('floor-prev').disabled=floorPage===0;$('floor-next').disabled=floorPage+1>=view.pages;$('floor-empty').hidden=Boolean(view.total);
 $('booth-list').replaceChildren();for(const x of view.items){const b=node('button',x.id+' · '+x.availabilityLabel);b.type='button';b.onclick=()=>inspect('strategy',x.id);$('booth-list').append(b);}
 $('floor-economics').textContent='MIN '+(configuration.minimum_units??'—')+' WHOLE UNIT · TRADE USD '+(ArenaProjection.amount(configuration.trade_fee)??'—')+' / SETTLEMENT · INTELLIGENCE USD '+(ArenaProjection.amount(configuration.intelligence_fee)??'—')+' / DELIVERY';
 $('floor-feed').replaceChildren();for(const e of [...events].reverse().slice(0,12)){const b=node('button',e.operation+(e.strategy_id?' · '+e.strategy_id:''));b.append(node('small',new Date(e.occurred_at).toLocaleString()+' · '+e.agent_id));b.onclick=()=>inspect('event',e.event_id);$('floor-feed').append(b);}if(!events.length)$('floor-feed').append(node('p','No recorded activity.'));
 if(selected)inspect(selected.kind,selected.id);
}
function viewFloor(show){$('floor-pane').hidden=!show;$('audit-pane').hidden=show;$('show-floor').setAttribute('aria-pressed',String(show));$('show-audit').setAttribute('aria-pressed',String(!show));if(show){floor.resize();renderFloor();}}
$('show-floor').onclick=()=>viewFloor(true);$('show-audit').onclick=()=>viewFloor(false);
$('floor-availability').onchange=$('floor-search').oninput=()=>{floorPage=0;renderFloor();};
$('floor-prev').onclick=()=>{floorPage--;renderFloor();};$('floor-next').onclick=()=>{floorPage++;renderFloor();};
$('floor-orbit').onclick=()=>{floor.auto=!floor.auto;$('floor-orbit').setAttribute('aria-pressed',String(floor.auto));};
$('floor-zoom-in').onclick=()=>floor.zoom=Math.min(2,floor.zoom+.15);
$('floor-zoom-out').onclick=()=>floor.zoom=Math.max(.65,floor.zoom-.15);
$('floor-home').onclick=()=>{floor.yaw=-.36;floor.pitch=.76;floor.zoom=1;floor.auto=false;$('floor-orbit').setAttribute('aria-pressed','false');};
window.addEventListener('resize',()=>{if(!$('floor-pane').hidden)renderFloor();});

function status(message,error=false){$('arena-status').textContent=message;$('arena-status').classList.toggle('error',error);}
async function api(path){const generation=session;const response=await fetch(path,{headers:{Authorization:'Bearer '+token}});const data=await response.json();if(generation!==session)throw new Error('Previous session discarded');if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'API request failed ('+response.status+'). Check filters and credential.');return data;}
function stop(){live=false;liveVersion++;clearTimeout(timer);timer=null;$('arena-live').textContent='Start live updates';}
function startLive(immediate=false){stop();live=true;const version=liveVersion;$('arena-live').textContent='Stop live updates';if(immediate)tick(version);else timer=setTimeout(()=>tick(version),pollSeconds*1000);}
function clear(){catalogue=[];connected=[];configuration={};floorPage=0;floorInstance='';selected=null;floor.auto=false;floor.selected=null;floor.bots.clear();floor.update({agents:[],instruments:[],events:[],eventId:0,queryFee:'—'});$('floor-inspector').replaceChildren();$('inspect-title').textContent='Select a booth';$('floor-search').value='';$('floor-availability').value='all';for(const id of ['floor-feed','booth-list'])$(id).replaceChildren();session++;requestVersion++;stop();token='';cursor=0;instance='';events=[];filters=new URLSearchParams();$('arena-filters').reset();for(const id of ['presence','available-inventory','arena-events'])$(id).replaceChildren();$('presence-count').textContent='0';$('event-count').textContent='';$('event-scope').textContent='';$('arena-asof').textContent='';$('arena-workspace').hidden=true;$('arena-access').hidden=false;$('connection-state').textContent='Not connected';$('arena-token').value='';}
function renderPresence(data){$('presence-count').textContent=String(data.items.length);$('presence').replaceChildren();for(const agent of data.items){const row=node('div','','presence-item');row.append(node('small',agent.agent_id),node('p','Last seen '+new Date(agent.last_seen*1000).toLocaleString()));$('presence').append(row);}if(!data.items.length)$('presence').append(node('p','No active connections.','empty'));}
function renderInventory(data){$('available-inventory').replaceChildren();for(const item of data.items.filter(x=>x.available_to_buy)){const row=node('div','','inventory-item');row.append(node('p',item.strategy_id),node('p',item.available_units+' units available · USD '+item.price.unit_price),node('small',item.price.provenance));$('available-inventory').append(row);}if(!data.items.length)$('available-inventory').append(node('p','No priced strategies currently available.','empty'));}
function renderEvents(retainedLimit){const opened=new Set([...$('arena-events').querySelectorAll('details[open]')].map(el=>el.dataset.eventId));$('arena-events').replaceChildren();for(const event of [...events].reverse()){
 const d=event.details,article=node('article','','event');article.dataset.operation=event.operation;
 let title=event.operation;
 if(event.operation==='BUY'||event.operation==='SELL')title+=' '+d.units+' '+event.strategy_id+' at USD '+d.unit_price;
 else if(event.operation==='QUERY')title+=' · '+d.kind+' · '+d.result_count+' results ('+d.mode+')';
 else if(event.operation==='REPORT')title+=' · '+d.action+' (not another trade)';
 else if(event.operation==='REJECTED')title+=' · '+(event.strategy_id||'historical strategy unavailable');
 article.append(node('time',new Date(event.occurred_at).toLocaleString()),node('h3',title),node('p','Agent '+event.agent_id,'actor'));
 if('available_units_after' in d)article.append(node('p','Inventory at settlement: '+d.available_units_before+' → '+d.available_units_after+' available units','effect'));
 if(event.operation==='QUERY')article.append(node('p',d.strategy_ids.join(', '),'record'));
 const detail=document.createElement('details');detail.dataset.eventId=event.event_id;detail.open=opened.has(event.event_id);detail.append(node('summary','Inspect event '+event.cursor),node('pre',JSON.stringify(event,null,2)));article.append(detail);$('arena-events').append(article);
 }if(!events.length)$('arena-events').append(node('p','No activity matches these filters.','empty'));$('event-count').textContent=events.length+' EVENT'+(events.length===1?'':'S');$('event-scope').textContent='Latest '+retainedLimit+' matching events retained in feed order · cursor '+cursor+'. Full history remains available through the API.';}
async function refresh(reset=false){const version=++requestVersion;
 const config=await api('/v1/exchange');let next=reset||instance!==config.instance_id?0:cursor;let collected=next===0?[]:[...events];
 const [presence,inventory]=await Promise.all([api('/v1/arena/connections'),api('/v1/strategies?availability=all')]);
 while(true){const params=new URLSearchParams(filters);params.set('after',String(next));params.set('limit',String(config.configuration.activity_page_size));const page=await api('/v1/arena/activity?'+params);if(version!==requestVersion)return;collected.push(...page.items);next=page.next_cursor;if(!page.has_more)break;}
 if(version!==requestVersion)return;instance=config.instance_id;cursor=next;pollSeconds=config.configuration.view_poll_seconds;events=[...new Map(collected.map(e=>[e.event_id,e])).values()].sort((a,b)=>a.cursor-b.cursor).slice(-config.configuration.activity_page_size);
 catalogue=inventory.items;connected=presence.items;configuration=config.configuration;const animate=floorInstance===instance&&!reset;floorInstance=instance;renderPresence(presence);renderInventory(inventory);renderEvents(config.configuration.activity_page_size);renderFloor(animate);$('connection-state').textContent='Instance '+instance;$('arena-asof').textContent='Updated '+new Date().toLocaleTimeString()+' · display interval '+pollSeconds+'s';
}
async function tick(version){if(!live||version!==liveVersion)return;const generation=session;try{await refresh();if(generation!==session||version!==liveVersion)return;if(live)status('Live display updated.');}catch(error){if(generation!==session||version!==liveVersion)return;stop();status(error.message,true);}if(live)timer=setTimeout(()=>tick(version),pollSeconds*1000);}
$('arena-access').onsubmit=async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;session++;token=$('arena-token').value.trim();try{await api('/v1/me');await refresh(true);$('arena-token').value='';$('arena-access').hidden=true;$('arena-workspace').hidden=false;viewFloor(true);startLive();status('Connected. Live Arena updates are automatic.');}catch(error){clear();status(error.message,true);}finally{button.disabled=false;}};
$('arena-refresh').onclick=async()=>{try{await refresh();status('Updated from the API.');}catch(error){status(error.message,true);}};
$('arena-live').onclick=()=>{if(live){stop();status('Live display updates stopped. Agents are unaffected.');}else startLive(true);};
$('arena-signout').onclick=()=>{clear();status('Signed out. No credential retained.');};
$('arena-filters').onsubmit=async event=>{event.preventDefault();filters=new URLSearchParams();for(const [id,key] of [['filter-agent','agent_id'],['filter-strategy','strategy_id'],['filter-operation','operation']])if($(id).value.trim())filters.set(key,$(id).value.trim());for(const [id,key] of [['filter-from','from'],['filter-to','to']])if($(id).value)filters.set(key,new Date($(id).value).toISOString());try{await refresh(true);status('Activity filters applied.');}catch(error){status(error.message,true);}};
$('clear-filters').onclick=async()=>{$('arena-filters').reset();filters=new URLSearchParams();try{await refresh(true);status('Activity filters cleared.');}catch(error){status(error.message,true);}};
})();
