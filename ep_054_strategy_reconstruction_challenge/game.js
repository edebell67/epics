(() => {
  'use strict';
  const sourceSnapshotDate = '2026-09-23';
  const evidenceWindow = '30 matched historical/replay tests on 23 September 2026';
  const scenario = {
    id: 'HSRC-001',
    title: 'The Split Route',
    graceSeconds: 90,
    steps: [
      {title:'Lock the case', prompt:'Which comparison rule keeps the reconstruction fair?', context:'You can inspect a result only after proving the two modes faced the same selected strategy basket.', correct:0, options:[
        ['Use the same basket in both modes','The route begins with a matched comparison.','+30'],
        ['Compare any two attractive outcomes','That introduces a selection mismatch.','−20'],
        ['Ignore the selected records','The source route cannot be reproduced without them.','−20']
      ]},
      {title:'Inspect the route', prompt:'Which evidence is most useful before accepting a headline result?', context:'A route can look convincing while hiding how much activity it required.', correct:1, options:[
        ['Only the higher aggregate result','A single headline cannot explain the route.','−20'],
        ['Closed rotations in each mode','Correct: activity is part of the recorded evidence.','+30'],
        ['A new current-date record','This case is fixed to its historical snapshot.','−20']
      ]},
      {title:'Check the challenge', prompt:'Which counter-evidence must stay visible in the replay?', context:'A good reconstruction does not erase routes that produced a different result.', correct:2, options:[
        ['None; the larger total settles the case','The scenario requires contrary observations.','−20'],
        ['Only the most dramatic record','That is not a complete counter-evidence check.','−20'],
        ['8 Total-higher tests and 1 tie','Correct: the result was not unanimous.','+30']
      ]},
      {title:'State the limit', prompt:'What is the strongest defensible conclusion?', context:'Choose the statement that stays inside the fixed historical evidence window.', correct:1, options:[
        ['This mode will remain superior','The frozen case cannot establish a future result.','−20'],
        ['Split was higher more often in this dated sample','Correct: this is the limit of the observation.','+30'],
        ['Players should select the mode now','The game never gives a current selection instruction.','−20']
      ]}
    ]
  };
  const state = {index:0, gamePoints:0, elapsedSeconds:0, paused:false, choices:[], completion:false, timer:null, startedAt:null};
  const $ = id => document.getElementById(id);
  const format = total => `${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`;
  const save = () => localStorage.setItem('hsrc-001', JSON.stringify({...state, timer:null}));
  const reset = () => {clearInterval(state.timer);Object.assign(state,{index:0,gamePoints:0,elapsedSeconds:0,paused:false,choices:[],completion:false,timer:null,startedAt:Date.now()});localStorage.removeItem('hsrc-001');};
  const renderMap = () => {$('gameMap').innerHTML=scenario.steps.map((step,i)=>{const choice=state.choices[i];const cls=i===state.index&&!state.completion?'active':choice?(choice.correct?'correct':'missed'):'';return `<div class="node ${cls}">${i+1}</div>`;}).join('');};
  const tick = () => {if(!state.paused&&!state.completion){state.elapsedSeconds+=1;$('timer').textContent=format(state.elapsedSeconds);save();}};
  const render = () => {
    const step=scenario.steps[state.index];
    $('points').textContent=state.gamePoints;$('timer').textContent=format(state.elapsedSeconds);$('step').textContent=`${state.index} / ${scenario.steps.length}`;$('sourceLabel').textContent=`SOURCE SNAPSHOT ${sourceSnapshotDate} · ${evidenceWindow} · GAME POINTS ONLY`;
    renderMap();
    if(!step) return complete();
    $('mapTitle').textContent=step.title;$('prompt').textContent=step.prompt;$('context').textContent=step.context;$('feedback').textContent='';$('feedback').className='feedback';
    $('choiceGrid').replaceChildren(...step.options.map((item,i)=>{const button=document.createElement('button');button.className='choice';button.innerHTML=`<span class="letter">${String.fromCharCode(65+i)}</span><span>${item[0]}<small>${item[2]} game points</small></span>`;button.onclick=()=>choose(i);return button;}));
  };
  const choose = selected => {
    const step=scenario.steps[state.index]; const correct=selected===step.correct; const delta=correct?30:-20;
    state.gamePoints+=delta;state.choices.push({junction:step.title,selected:step.options[selected][0],correct,delta,explanation:step.options[selected][1],at:state.elapsedSeconds});
    $('feedback').textContent=step.options[selected][1];$('feedback').className=`feedback ${correct?'good':'bad'}`;
    [...$('choiceGrid').children].forEach(button=>button.disabled=true);$('points').textContent=state.gamePoints;renderMap();save();
    setTimeout(()=>{state.index+=1;render();},750);
  };
  const complete = () => {
    state.completion=true;clearInterval(state.timer);const penalty=Math.max(0,state.elapsedSeconds-scenario.graceSeconds);state.gamePoints-=penalty;$('points').textContent=state.gamePoints;$('game').hidden=true;$('result').hidden=false;$('resultTitle').textContent=state.gamePoints>=80?'Route reconstructed':'Route complete — review the missed evidence';$('resultCopy').textContent=state.gamePoints>=80?'You held the comparison to its dated evidence, inspected activity and retained the counter-evidence.':'You completed the route, but the replay shows where the historical evidence was weakened.';$('finalPoints').textContent=state.gamePoints;$('finalTime').textContent=format(state.elapsedSeconds);$('routeScore').textContent=`${state.choices.filter(x=>x.correct).length} / ${scenario.steps.length}`;$('statusBadge').textContent='COMPLETE';save();
  };
  const replay = () => {$('replayPanel').hidden=false;$('replaySteps').innerHTML=state.choices.map((choice,i)=>`<article class="replay-step ${choice.correct?'good':'bad'}"><b>${i+1}. ${choice.junction} · ${choice.delta>0?'+':''}${choice.delta} points</b><div>${choice.selected}</div><small>${choice.explanation} · ${format(choice.at)}</small></article>`).join('');$('replayPanel').scrollIntoView({behavior:'smooth'});};
  $('startGame').onclick=()=>{reset();$('intro').hidden=true;$('game').hidden=false;state.timer=setInterval(tick,1000);render();};
  $('pauseGame').onclick=()=>{state.paused=!state.paused;$('pauseGame').textContent=state.paused?'Resume':'Pause';$('statusBadge').textContent=state.paused?'PAUSED':'PLAYING';save();};
  $('restartGame').onclick=()=>{reset();$('result').hidden=true;$('replayPanel').hidden=true;$('intro').hidden=false;};
  $('replayGame').onclick=replay;
})();
