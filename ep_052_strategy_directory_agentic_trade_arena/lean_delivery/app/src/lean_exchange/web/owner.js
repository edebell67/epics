// VERSION HISTORY v1.1.1 · 2026-09-02 · Format exact zeros legibly and discard superseded portfolio/attribution responses.
// v1.1.0 · 2026-09-02 · Render owner-scoped portfolio and dated record-linked attribution without browser accounting.
// v1.0.2 · 2026-09-02 · Discard responses from an earlier login after sign-out to avoid stale private UI state.
// v1.0.1 · 2026-09-02 · Show newest feedback first and page backwards without skipping messages.
// v1.0.0 · 2026-09-02 · Owner feedback via scoped APIs; credentials stay in memory and all user text uses textContent.
(()=>{'use strict';
let session=0,token='',agents=[],messages=[],cursor=0,pending=null,positionRequest=0,attributionRequest=0;
const $=id=>document.getElementById(id);
const text=(tag,value,cls)=>{const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;};
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
async function api(path,options={}){const generation=session;const response=await fetch(path,{...options,headers:{'Authorization':'Bearer '+token,...(options.body?{'Content-Type':'application/json'}:{}),...options.headers}});const body=await response.json();if(generation!==session)throw new Error('Previous session request discarded.');if(!response.ok){if(response.status===401)throw new Error('Credential expired or revoked. Sign out and connect with a new credential.');throw new Error(typeof body.detail==='string'?body.detail:'Request failed ('+response.status+').');}return body;}
function renderAgents(){const selected=new Set([...$('agents').querySelectorAll('input:checked')].map(x=>x.value));$('agents').replaceChildren();for(const agent of agents){const row=text('div','','recipient'),input=document.createElement('input'),label=document.createElement('label');input.type='checkbox';input.value=agent.id;input.id='agent-'+agent.id;input.checked=selected.has(agent.id);label.htmlFor=input.id;label.append(text('span',agent.name),text('small',agent.id));row.append(input,label);$('agents').append(row);}if(!agents.length)$('agents').append(text('p','No agents registered. Register an agent through the owner API.','empty'));$('summary').textContent=agents.length+' registered agent'+(agents.length===1?'':'s');}
function renderThreads(){const names=new Map(agents.map(a=>[a.id,a.name]));$('threads').replaceChildren();for(const message of [...messages].sort((a,b)=>b.cursor-a.cursor)){const article=text('article','','thread');article.dataset.feedbackId=message.id;article.append(text('time',new Date(message.created_at).toLocaleString()),text('p',message.message,'message'));for(const recipient of message.recipients)article.append(text('div',(names.get(recipient.agent_id)||recipient.agent_id)+' · '+(recipient.acknowledged_at?'Acknowledged '+new Date(recipient.acknowledged_at).toLocaleString():'Awaiting acknowledgement'),'receipt'));for(const reply of message.replies){const block=text('div','','reply');block.append(text('small',(names.get(reply.agent_id)||reply.agent_id)+' replied'),text('p',reply.message));article.append(block);}$('threads').append(article);}if(!messages.length)$('threads').append(text('p','No feedback yet. Select an agent and send a message.','empty'));$('history-count').textContent=messages.length+' MESSAGES';}
async function refresh(){const agentData=await api('/v1/owner/agents');agents=agentData.items;renderAgents();const data=await api('/v1/owner/feedback?latest=true');const updates=await Promise.all(messages.filter(x=>!data.items.some(y=>y.id===x.id)).map(x=>api('/v1/owner/feedback/'+x.id)));const merged=new Map([...messages,...updates,...data.items].map(x=>[x.id,x]));messages=[...merged.values()];cursor=cursor?Math.min(cursor,data.next_cursor||cursor):data.next_cursor;$('more').hidden=data.items.length===0;renderThreads();await loadPositions();}
$('access').addEventListener('submit',async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;session++;token=$('token').value.trim();try{const identity=await api('/v1/me');if(identity.role!=='owner')throw new Error('Use an owner credential, not an agent credential.');await refresh();$('identity').textContent='Owner '+identity.owner_id;$('token').value='';$('access').hidden=true;$('workspace').hidden=false;status('Connected. Refresh to read new acknowledgements and replies.');}catch(error){token='';status(error.message,true);}finally{button.disabled=false;}});
$('refresh').onclick=async()=>{try{await refresh();status('Updated from the API.');}catch(error){status(error.message,true);}};
$('signout').onclick=()=>{session++;token='';agents=[];messages=[];cursor=0;pending=null;for(const id of ['agents','threads','positions','portfolio-totals','explain-agents','attribution'])$(id).replaceChildren();$('value-from').value='';$('value-to').value='';$('position-scope').textContent='';$('message').value='';$('identity').textContent='Not connected';$('workspace').hidden=true;$('access').hidden=false;status('Signed out. No credential retained.');};
$('compose').addEventListener('submit',async event=>{event.preventDefault();const selected=[...$('agents').querySelectorAll('input:checked')].map(x=>x.value),message=$('message').value.trim();if(!selected.length){status('Select at least one recipient.',true);return;}if(!message)return;const content=JSON.stringify({agent_ids:selected,message});if(!pending||pending.content!==content)pending={content,request_id:crypto.randomUUID()};$('send').disabled=true;try{const result=await api('/v1/owner/feedback',{method:'POST',body:JSON.stringify({...JSON.parse(content),request_id:pending.request_id})});messages.push(result);messages=[...new Map(messages.map(x=>[x.id,x])).values()];pending=null;$('message').value='';renderThreads();status('Feedback sent. The agent decides how to respond.');}catch(error){status(error.message+' Retry preserves the same request identity.',true);}finally{$('send').disabled=false;}});
$('more').onclick=async()=>{try{const data=await api('/v1/owner/feedback?before='+cursor);messages=[...new Map([...messages,...data.items].map(x=>[x.id,x])).values()];cursor=data.next_cursor;$('more').hidden=!data.items.length;renderThreads();}catch(error){status(error.message,true);}};
// Preserve API decimal strings: no floating-point accounting or rounding in the browser.
const usd=value=>value===null?'Unavailable':'USD '+(/^[+-]?0(?:\.0*)?(?:E[+-]?\d+)?$/i.test(String(value))?'0.00':String(value).replace(/(\.\d{2,}?)0+$/,'$1'));
function metrics(values){const list=text('dl','','figures');for(const [label,value] of values){const row=document.createElement('div');row.append(text('dt',label),text('dd',value));list.append(row);}return list;}
function disclosure(label,content){const node=document.createElement('details');node.append(text('summary',label),content);return node;}
function localTime(value){const date=new Date(value);return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,23);}
async function loadPositions(){
  const requestVersion=++positionRequest;attributionRequest++;
  const selected=[...$('agents').querySelectorAll('input:checked')].map(x=>x.value);
  const params=new URLSearchParams();for(const id of selected)params.append('agent_id',id);
  const data=await api('/v1/owner/positions?'+params);
  if(requestVersion!==positionRequest)return;
  $('position-scope').textContent=data.agent_count+' agent'+(data.agent_count===1?'':'s')+' · as of '+new Date(data.as_of).toLocaleString()+' · '+(data.valuation_complete?'Published-price valuation':'Incomplete valuation — missing prices');
  $('portfolio-totals').replaceChildren(metrics([['Spendable funds',usd(data.totals.spendable_usd)],['Holdings',usd(data.totals.holdings_value_usd)],['Total value',usd(data.totals.total_value_usd)],['Gain since seed',usd(data.totals.gain_since_seed_usd)]]));
  $('positions').replaceChildren();$('explain-agents').replaceChildren();$('attribution').replaceChildren();
  const names=new Map(agents.map(a=>[a.id,a.name]));
  for(const agent of data.agents){
    const content=document.createElement('div');content.append(metrics([['Seed',usd(agent.seed_usd)],['Trade fees',usd(agent.trade_fees_usd)],['Query fees',usd(agent.intelligence_fees_usd)]]));
    for(const holding of agent.positions){
      const item=text('section','','holding');item.append(text('h3',holding.strategy_id+' · '+holding.units+' whole units'),text('p',usd(holding.marked_value_usd)+' at '+(holding.price?usd(holding.price.unit_price)+' / unit':'unavailable price')));
      if(holding.price)item.append(text('p',holding.price.provenance+' · '+holding.price.price_version+' · published '+holding.price.published_at,'provenance'));
      const entries=document.createElement('div');entries.append(text('p',holding.entry_note,'muted'));
      for(const entry of holding.entry_trades)entries.append(text('p',entry.units+' units at '+usd(entry.unit_price)+' · fee '+usd(entry.fee)+' · '+entry.executed_at+' · trade '+entry.trade_id,'record'));
      item.append(disclosure('Entry receipts ('+holding.entry_trades.length+')',entries));content.append(item);
    }
    if(!agent.positions.length)content.append(text('p','No open positions.','muted'));
    $('positions').append(disclosure((names.get(agent.agent_id)||agent.agent_id)+' · '+usd(agent.total_value_usd),content));
    const explain=text('button','Explain '+(names.get(agent.agent_id)||agent.agent_id),'quiet');explain.type='button';explain.onclick=()=>explainChange(agent.agent_id);$('explain-agents').append(explain);
  }
  if(!$('value-from').value&&data.agents.length)$('value-from').value=localTime(new Date(new Date(data.agents.map(a=>a.allocation_created_at).sort().at(-1)).getTime()+1));
  $('value-to').value=localTime(data.as_of);
}
async function explainChange(agentId){try{
  const requestVersion=++attributionRequest;
  if(!$('value-from').value||!$('value-to').value)throw new Error('Choose both interval dates.');
  const params=new URLSearchParams({from:new Date($('value-from').value).toISOString(),to:new Date($('value-to').value).toISOString()});
  const data=await api('/v1/owner/agents/'+agentId+'/value-change?'+params);
  if(requestVersion!==attributionRequest)return;
  $('attribution').replaceChildren(text('h3',data.reconciled?'Value change reconciled':'Value change could not be reconciled'));
  $('attribution').append(metrics([['Opening total',usd(data.opening.total_value_usd)],['Closing total',usd(data.closing.total_value_usd)],['Value change',usd(data.value_change_usd)],['Cash change',usd(data.cash_change_usd)],['Price / trade gain',usd(data.price_and_trade_gain_usd)],['Trade fees',usd(data.trade_fees_usd)],['Query fees',usd(data.intelligence_fees_usd)],['Difference',usd(data.reconciliation_difference_usd)]]),text('p',data.formula,'muted'));
  for(const line of data.strategies){const detail=document.createElement('div');detail.append(text('p','Units '+line.opening_units+' → '+line.closing_units+' · '+usd(line.price_and_trade_gain_usd)));
    for(const [label,quote] of [['Opening',line.opening_price],['Closing',line.closing_price]])detail.append(text('p',label+': '+(quote?usd(quote.unit_price)+' · '+quote.price_version+' · '+quote.provenance:'No published quote'),'record'));
    for(const trade of line.trade_effects)detail.append(text('p',trade.side+' '+trade.units+' at '+usd(trade.execution_price_usd)+' · effect '+usd(trade.value_change_usd)+' · fee '+usd(trade.fee_usd)+' · trade '+trade.trade_id,'record'));
    $('attribution').append(disclosure(line.strategy_id+' — price and trade details',detail));}
  for(const charge of data.query_charges)$('attribution').append(text('p','Query charge '+usd(charge.amount_usd)+' · movement '+charge.id+' · '+charge.operation_id,'record'));
  status('Value-change details loaded from recorded API data.');
}catch(error){status(error.message,true);}}
$('load-positions').onclick=async()=>{try{await loadPositions();status('Selected positions loaded.');}catch(error){status(error.message,true);}};
})();
