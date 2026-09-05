// VERSION HISTORY v1.1.1 · 2026-09-02 · Parent status and evidence aggregate actual child gates.
// v1.1.0 · 2026-09-02 · Derive progress from node evidence and expose test links.
// v1.0.0 · 2026-09-02 · EP047/previous-EP052 style filters, hierarchy and inspector.
(function(){
'use strict';
const data=window.EP052_WORKFLOW,page=document.body.dataset.page,master=page==='master';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const phase=master?null:data.phases.find(p=>p.id===page);
const nodes=master?data.phases.map(p=>({id:p.id,lane:p.id,title:p.title,purpose:p.purpose,pct:Math.round(data.nodes.filter(n=>n.lane===p.id).reduce((s,n)=>s+n.pct,0)/4),status:data.nodes.filter(n=>n.lane===p.id).every(n=>n.pct===100)?'Complete':data.nodes.some(n=>n.lane===p.id&&n.pct>0)?'In progress':'Not started',inputs:'Approved lean scope and preceding delivery dependencies',steps:data.nodes.filter(n=>n.lane===p.id).map(n=>n.id+' · '+n.title),test:'All four child gates pass their named completion tests.',evidence:data.nodes.filter(n=>n.lane===p.id).map(n=>n.id+': '+n.status+' — '+n.evidence).join('\n'),dependencies:p.id==='L1'?'Lean specification v1.3':('Earlier phase contracts; see leaf dependencies'),executor:'Implementation guide: skills/ep052-'+p.id.toLowerCase()+'/SKILL.md',outputs:'Four evidence-backed child gates',child:'workflows/EP052_'+p.id.toLowerCase()+'_workflow.html'})):data.nodes.filter(n=>n.lane===page);
document.querySelector('#nodeCount').textContent=nodes.length;
document.querySelector('#coverage').textContent=Math.round(nodes.reduce((s,n)=>s+n.pct,0)/nodes.length)+'%';
const toolbar=document.querySelector('.toolbar');
toolbar.innerHTML='<button class="on" data-filter="all">All steps</button>'+ (master?data.phases:[phase]).map(p=>'<button data-filter="'+p.id+'">'+esc(p.id+' · '+p.title)+'</button>').join('');
function select(id){
const n=nodes.find(n=>n.id===id);if(!n)return;
document.querySelectorAll('.node').forEach(b=>{b.classList.toggle('sel',b.dataset.id===id);b.setAttribute('aria-pressed',String(b.dataset.id===id));});
document.querySelector('#side').innerHTML='<h2>'+esc(n.title)+'</h2><p class="sub">'+esc(n.id)+' · '+n.pct+'% · '+esc(n.status)+'</p><p>'+esc(n.purpose)+'</p><h4>Inputs</h4><p>'+esc(n.inputs)+'</p><h4>Implementation steps</h4><ol>'+n.steps.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ol><h4>Completion test</h4><p class="box test">'+esc(n.test)+'</p><h4>Evidence / required evidence</h4><p class="box ev">'+esc(n.evidence)+'</p><h4>Dependencies</h4><p class="box dep">'+esc(n.dependencies)+'</p><h4>Planned executor / implementation guide</h4><p class="box auto">'+esc(n.executor)+'</p><h4>Outputs</h4><p>'+esc(n.outputs)+'</p>'+(n.deliverable?'<a class="child" href="'+esc(n.deliverable)+'" target="_blank" rel="noopener">Open testable deliverable →</a>':'')+(n.child?'<a class="child" href="'+n.child+'">Open dedicated child workflow →</a>':'');
}
function render(filter){
const visible=nodes.filter(n=>filter==='all'||n.lane===filter);
document.querySelector('#map').innerHTML=(master?data.phases:[phase]).map(p=>{const list=visible.filter(n=>n.lane===p.id);if(!list.length)return '';return '<section class="lane"><h2>'+esc(p.id+' · '+p.title)+'</h2><p class="who">'+esc(p.purpose)+'</p><div class="flow">'+list.map(n=>'<button class="node" data-id="'+n.id+'"><span class="tag">'+esc(n.id)+'</span><h3>'+esc(n.title)+'</h3><p>'+esc(n.purpose)+'</p><span class="stage">'+(master?'4 detailed gates · click to open inspector':'Planned code and test in inspector')+'</span><span class="progress '+(n.pct===100?'complete':n.pct?'partial':'planned')+'">'+n.pct+'% · '+esc(n.status)+'</span></button>').join('')+'</div></section>';}).join('');
document.querySelectorAll('.node').forEach(b=>b.onclick=()=>select(b.dataset.id)); if(visible[0])select(visible[0].id);
}
toolbar.querySelectorAll('button').forEach(b=>b.onclick=()=>{toolbar.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render(b.dataset.filter);});
render('all');if(location.hash)select(location.hash.slice(1));
})();
