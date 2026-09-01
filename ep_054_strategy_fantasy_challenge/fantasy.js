/* Version history
 * v2.0.0 · 2026-08-31 · Replaces strategy fixtures and simulated scoring with EP051-backed catalogue and rankings.
 * v1.3.0 · 2026-08-31 · Adds attributable friend invitations into the same Global Challenge.
 * v1.2.0 · 2026-08-31 · Narrows the MVP to build, enter, live rank and share.
 * v1.1.0 · 2026-08-31 · Introduced deterministic position-movement exploration.
 * v1.0.0 · 2026-08-31 · Version history added; file predates this convention.
 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = {
    entered: false, running: false, beat: 0, timer: null, invite: null, entryId: null,
    strategies: [], candidates: [], catalogue: [], competitors: [], directorySource: null,
    previousRanks: {}
  };
  const portfolioName = () => $('portfolioName').value.trim() || 'Untitled Portfolio';
  const api = async (path, options={}) => { const response=await fetch(path,{headers:{'Content-Type':'application/json'},...options}); if(!response.ok) throw new Error((await response.json()).detail||`Request failed: ${response.status}`); return response.json(); };
  const ranked = () => [...state.competitors].sort((a,b)=>b.score-a.score).map((row,index)=>({...row,rank:index+1}));
  const announce = (kind,text) => {
    $('eventStatus').textContent=kind;
    const row=document.createElement('div'); row.className='event';
    const title=document.createElement('b'); title.textContent=kind;
    row.append(title,document.createTextNode(` · ${text}`)); $('destinationEvents').prepend(row);
  };
  const renderStrategies = () => {
    $('strategyCount').textContent=`${state.strategies.length} / 10 selected`;
    $('portfolioStrategies').replaceChildren(...state.strategies.map((s,index)=>{
      const row=document.createElement('article'); row.className='strategy';
      const copy=document.createElement('div'); const meta=document.createElement('small'); meta.textContent=`${s[0]} · ${s[2]}`; const name=document.createElement('b'); name.textContent=s[1]; copy.append(meta,name);
      const remove=document.createElement('button'); remove.textContent='×'; remove.setAttribute('aria-label',`Remove ${s[1]}`); remove.onclick=()=>{state.strategies.splice(index,1);renderStrategies();renderAvailable();};
      row.append(copy,remove); return row;
    }));
    $('enterGlobal').disabled=state.entered||state.strategies.length<3;
    $('enterGlobal').innerHTML=state.strategies.length<3?`Select ${3-state.strategies.length} more ${state.strategies.length===2?'strategy':'strategies'} <b>↗</b>`:'Enter Global Challenge <b>↗</b>';
  };
  const renderAvailable = () => {
    const query=$('strategySearch').value.trim().toLowerCase(), sort=$('strategySort').value;
    const selected=new Set(state.strategies.map(item=>item[0]));
    let rows=state.catalogue.filter(item=>!selected.has(item[0])&&(!query||item[0].toLowerCase().includes(query)||item[1].toLowerCase().includes(query)));
    rows.sort((a,b)=>sort==='return_desc'?b[3]-a[3]:sort==='trades_desc'?b[4]-a[4]:a[0].localeCompare(b[0]));
    $('availableCount').textContent=`${rows.length} choices`;
    $('availableStrategies').innerHTML=rows.slice(0,30).map(item=>`<article class="available-strategy"><div><small>${item[0]} · ${item[4]} trades today</small><b>${item[1]}</b><span class="metric ${item[3]>=0?'positive':'negative'}">${item[3]>=0?'+':''}${item[3].toFixed(2)} net return</span><span class="metric">${item[5]===null?'—':(item[5]*100).toFixed(1)+'%'} win rate</span></div><button data-strategy-id="${item[0]}" ${state.strategies.length>=10?'disabled':''}>Select +</button></article>`).join('')||'<p class="help">No available strategies match this search.</p>';
    $('availableStrategies').querySelectorAll('[data-strategy-id]').forEach(button=>button.onclick=()=>{const item=state.catalogue.find(row=>row[0]===button.dataset.strategyId);if(item&&state.strategies.length<10){state.strategies.push(item);renderStrategies();renderAvailable();}});
  };
  const renderRanks = (direction='') => {
    const rows=ranked(), me=rows.find(row=>row.me), container=$('neighbourRows');
    if(!rows.length){container.innerHTML='<p class="help">No verified Global Challenge entries yet.</p>';$('leaderboardRows').innerHTML='<p class="help">The leaderboard appears after the first evidence-backed entry.</p>';return null;}
    const old=new Map([...container.children].map(node=>[node.dataset.portfolioKey,node.getBoundingClientRect().top]));
    const start=me?Math.max(0,Math.min(rows.length-5,me.rank-3)):0;
    container.innerHTML=rows.slice(start,start+5).map(row=>{
      const prior=state.previousRanks[row.key]??row.rank, delta=prior-row.rank;
      return `<article class="neighbour-row ${row.me?'me':''} ${row.me&&direction?`moved-${direction}`:''}" data-portfolio-key="${row.key}"><span class="rank-stack">#${row.rank}<small class="rank-change ${delta>0?'up':delta<0?'down':''}">${delta>0?`▲ ${delta}`:delta<0?`▼ ${Math.abs(delta)}`:'—'}</small></span><div><b>${row.name}</b><small>${row.me?'YOUR VERIFIED ENTRY':'GLOBAL CHALLENGE ENTRY'}</small></div><span class="score-stack">${row.score.toFixed(2)}<small>net pts</small></span></article>`;
    }).join('');
    [...container.children].forEach(node=>{const top=old.get(node.dataset.portfolioKey);if(top!==undefined){const shift=top-node.getBoundingClientRect().top;if(shift){node.style.transform=`translateY(${shift}px)`;requestAnimationFrame(()=>requestAnimationFrame(()=>node.style.transform=''));}}});
    rows.forEach(row=>state.previousRanks[row.key]=row.rank);
    $('leaderboardRows').innerHTML=rows.map(row=>`<article class="board-row ${row.me?'me':''}"><span class="rank">#${row.rank}</span><div><b>${row.name}</b><small>${row.me?'YOUR VERIFIED ENTRY':'GLOBAL CHALLENGE PARTICIPANT'}</small></div><span class="points">${row.score.toFixed(2)} net pts</span></article>`).join('');
    return me;
  };
  const advance = async () => {
    if(!state.entered||!state.entryId) return;
    state.beat+=1; const previous=state.previousRanks[state.entryId];
    const board=await api(`/api/leaderboard?entry_id=${encodeURIComponent(state.entryId)}`);
    state.competitors=board.rows.map(row=>({key:row.entry_id,name:`${row.display_name} · ${row.portfolio_name}`,score:Number(row.score),me:row.is_current,contributions:row.contributions||[]}));
    const after=board.current?.rank, direction=previous&&after<previous?'up':previous&&after>previous?'down':''; renderRanks(direction);
    $('pulseTick').textContent=`Refresh ${String(state.beat).padStart(2,'0')}`;
    const score=Number(board.current?.score||0),movement=previous&&after<previous?`rose to #${after}`:previous&&after>previous?`fell to #${after}`:`is #${after}`;
    $('captureCaption').textContent=`Updated ${new Date(board.updated_at).toLocaleTimeString()} · ${portfolioName()} ${movement} with ${score.toFixed(2)} evidence-backed net points.`;
    $('eventStatus').textContent=`EP051 RANK · #${after}`;
    if($('inviteDialog').open){$('inviteRank').textContent=`#${after}`;$('inviteCopy').textContent=`${portfolioName()} has ${score.toFixed(2)} net points. Your friend will build their own portfolio and join the same Global Challenge.`;}
  };
  const syncTimer = () => {
    clearInterval(state.timer);
    if(state.running) state.timer=setInterval(()=>advance().catch(error=>announce('RANK_REFRESH_FAILED',error.message)),15000);
    $('liveToggle').textContent=state.running?'Pause':'Resume';
    $('pulseStatus').innerHTML=`<i class="live-dot"></i>${state.entered?(state.running?'EP051 ranking live':'Verified ranking paused'):'Waiting for verified entry'}`;
  };
  $('addStrategy').onclick=()=>{};
  $('strategySearch').addEventListener('input',renderAvailable);
  $('strategySort').addEventListener('change',renderAvailable);
  $('enterGlobal').onclick=async()=>{
    if(!portfolioName()||state.strategies.length<3){announce('ENTRY BLOCKED','Name the portfolio and choose at least three EP051 strategies.');return;}
    $('enterGlobal').disabled=true;
    try{const entry=await api('/api/entries',{method:'POST',body:JSON.stringify({email:$('playerEmail').value,display_name:$('displayName').value,portfolio_name:portfolioName(),strategy_ids:state.strategies.map(item=>item[0])})});state.entryId=entry.entry_id;announce('ENTRY_PERSISTED',`${entry.entry_id} · ${entry.baseline_version} · ${entry.evidence.length} evidence baselines`);}catch(error){announce('ENTRY_BLOCKED',error.message);$('enterGlobal').disabled=false;return;}
    state.entered=true; state.running=true;
    $('challengeFriend').disabled=false; $('portfolioStatus').textContent=`ENTERED · ${state.strategies.length} EP051 strategies`; announce('GLOBAL ENTRY CREATED',`${portfolioName()} entered from verified EP051 baselines.`);syncTimer();await advance();$('livePosition').scrollIntoView({behavior:'smooth'});
  };
  $('liveToggle').onclick=()=>{if(!state.entered)return;state.running=!state.running;syncTimer();};
  const invitation=()=>{
    const me=ranked().find(row=>row.me);
    if(!state.invite||!me) throw new Error('Create a verified entry and invitation first.');
    const url=`${location.origin}${location.pathname.replace(/\/$/,'')}/invite/${state.invite.id}`;
    return {me,url,text:`I'm #${me.rank} in the Strategy Fantasy Global Challenge with ${me.score.toFixed(2)} evidence-backed net points. Can you build a portfolio that beats me? Join the same Global Challenge: ${url}`};
  };
  $('challengeFriend').onclick=async()=>{try{const persisted=await api('/api/invitations',{method:'POST',body:JSON.stringify({entry_id:state.entryId})});state.invite={id:persisted.invite_token,challenge:persisted.challenge_id,created_at:persisted.created_at,persisted:true};const invite=invitation();$('inviteRank').textContent=`#${invite.me.rank}`;$('inviteCopy').textContent=`${portfolioName()} has ${invite.me.score.toFixed(2)} evidence-backed net points. Your friend will build their own portfolio and join the same Global Challenge.`;$('inviteLink').value=invite.url;$('inviteStatus').textContent=`${state.invite.id} · persisted attributable invitation ready.`;$('inviteDialog').showModal();announce('INVITE_CREATED',`${state.invite.id} links back to the same Global Challenge.`);}catch(error){announce('INVITE_BLOCKED',error.message);}};
  $('shareInvite').onclick=async()=>{const invite=invitation();try{if(navigator.share){await navigator.share({title:'Can you beat my strategy portfolio?',text:invite.text,url:invite.url});$('inviteStatus').textContent='Native share sheet opened.';}else{await navigator.clipboard.writeText(invite.text);$('inviteStatus').textContent='Invitation message copied.';}announce('INVITE_SHARED',`${state.invite.id} shared from current rank #${invite.me.rank}.`);}catch(error){$('inviteStatus').textContent=error.name==='AbortError'?'Share cancelled.':'Sharing unavailable; copy the invitation link instead.';}};
  $('copyInvite').onclick=async()=>{const invite=invitation();try{await navigator.clipboard.writeText(invite.url);$('inviteStatus').textContent='Attributable invitation link copied.';announce('INVITE_SHARED',`${state.invite.id} copied for a friend.`);}catch{$('inviteLink').select();$('inviteStatus').textContent='Select and copy the invitation link above.';}};
  $('previewInvite').onclick=()=>{$('friendPreview').hidden=false;$('previewInvite').hidden=true;$('inviteStatus').textContent='Preview only: the link opens the normal entry journey.';announce('INVITE_OPENED',`${state.invite.id} opened in the friend-journey preview.`);};
  $('acceptPreview').onclick=async()=>{try{await api(`/api/invitations/${state.invite.id}/accept`,{method:'POST',body:JSON.stringify({email:'friend@example.test',display_name:'Invited friend'})});$('friendPreview').innerHTML='<b>CHALLENGE ACCEPTED</b><span>Your friend now chooses strategies and enters this same Global Challenge—no private competition was created.</span>';$('inviteStatus').textContent='Invitation accepted · same Global Challenge confirmed.';announce('INVITE_ACCEPTED',`${state.invite.id} attributed to a new entrant.`);}catch(error){announce('INVITE_ACCEPT_BLOCKED',error.message);}};
  $('portfolioName').addEventListener('input',()=>{const current=state.competitors.find(row=>row.me);if(current){current.name=portfolioName();renderRanks();}});
  $('resetDemo').onclick=()=>location.reload();
  document.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>button.closest('dialog').close());
  const loadDirectory=async()=>{try{const payload=await api('/api/strategies');state.directorySource=payload.source;state.catalogue=payload.strategies.map(row=>{const win=row.win_rate===null||row.win_rate===undefined?null:Number(row.win_rate);return [row.strategy_id,row.display_name,`${row.total_trades} trades today · ${Number(row.total_net_return)>=0?'+':''}${Number(row.total_net_return).toFixed(2)} net return · ${win===null?'—':(win*100).toFixed(1)+'%'} win rate · evidence ${row.evidence_end||'pending'}`,Number(row.total_net_return),Number(row.total_trades),win];});state.strategies=[];state.candidates=state.catalogue;renderStrategies();renderAvailable();$('eventStatus').textContent=`EP051 CURRENT · ${payload.source.eligibility_date}`;}catch(error){state.strategies=[];state.candidates=[];state.catalogue=[];$('strategyCount').textContent='0 current-date strategies';$('portfolioStrategies').innerHTML=`<p class="notice">${error.message}</p>`;$('availableStrategies').innerHTML='';$('addStrategy').disabled=true;$('enterGlobal').disabled=true;announce('NO CURRENT STRATEGIES','Entry disabled: historical strategies are excluded.');}renderRanks();syncTimer();};
  loadDirectory();
})();
