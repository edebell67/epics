(() => {
  'use strict';

  const sourceSnapshotDate = '2026-09-23';
  const evidenceWindow = 'DNA_200651 · CHF · fixed completed trade record';
  const graceSchedule = [10, 5, 3];
  const nodeGraph = { B:{x:22,y:39}, S:{x:50,y:18}, H:{x:78,y:39} };
  const scenario = {
    id: 'HSM-001', level: 1, title: 'Strategy Echo', graceSeconds: graceSchedule[0],
    steps: [
      { time:'01:39', title:'Opening signal', prompt:'What action does the strategy take?', context:'CHF · flat position · TP +100 · SL −30 · strategy rule: sp_001:dna2-trade', strategyAction:'B', outcome:'+70 historical result', closeType:'Reversed' },
      { time:'02:23', title:'First reversal', prompt:'What action does the strategy take?', context:'CHF · previous BUY closed +70 · new strategy event · TP +100 · SL −30', strategyAction:'S', outcome:'−40 historical result', closeType:'target reached' },
      { time:'04:30', title:'Return to route', prompt:'What action does the strategy take?', context:'CHF · previous SELL closed −40 · new strategy event · TP +100 · SL −30', strategyAction:'B', outcome:'+85 historical result', closeType:'Reversed' },
      { time:'07:59', title:'Second reversal', prompt:'What action does the strategy take?', context:'CHF · previous BUY closed +85 · new strategy event · TP +100 · SL −30', strategyAction:'S', outcome:'−40 historical result', closeType:'target reached' }
    ]
  };
  const state = { index:0, gamePoints:0, penaltyPoints:0, elapsedSeconds:0, turnSeconds:0, paused:false, choices:[], completion:false, timer:null, player:{x:50,y:83} };
  const $ = id => document.getElementById(id);
  const format = total => `${String(Math.floor(total / 60)).padStart(2,'0')}:${String(total % 60).padStart(2,'0')}`;
  const save = () => localStorage.setItem('hsm-001', JSON.stringify({...state, timer:null}));
  const reset = () => { clearInterval(state.timer); Object.assign(state,{index:0,gamePoints:0,penaltyPoints:0,elapsedSeconds:0,turnSeconds:0,paused:false,choices:[],completion:false,timer:null,player:{x:50,y:83}}); localStorage.removeItem('hsm-001'); };
  const movePlayer = node => { state.player={x:node.x,y:node.y}; const token=$('playerToken'); token.style.setProperty('--x',`${node.x}%`); token.style.setProperty('--y',`${node.y}%`); };
  // same action: 0 penalty; HOLD is close to BUY/SELL; BUY versus SELL is opposite.
  const actionPenalty = (strategyAction, playerAction) => {
    if (strategyAction === playerAction) return 0;
    if (strategyAction === 'H' || playerAction === 'H') return 10;
    return 20;
  };
  const timePenalty = seconds => Math.max(0, seconds - scenario.graceSeconds) * 10; // +10 per second after grace
  const buttons = () => [...document.querySelectorAll('[data-action]')];
  const setButtons = disabled => buttons().forEach(button => { button.disabled = disabled; button.classList.remove('selected'); });
  const render = () => {
    const step = scenario.steps[state.index];
    if (!step) return finish();
    state.turnSeconds = 0;
    $('penalty').textContent = state.penaltyPoints;
    $('timer').textContent = format(state.elapsedSeconds);
    $('grace').textContent = `${scenario.graceSeconds}s`;
    $('step').textContent = `${state.index + 1} / ${scenario.steps.length}`;
    $('mapTitle').textContent = `${step.title} · ${step.time}`;
    $('prompt').textContent = step.prompt;
    $('context').textContent = step.context;
    $('missionBadge').textContent = 'MIMIC THE ROUTE';
    $('feedback').textContent = '';
    $('feedback').className = 'feedback';
    $('continueGame').hidden = true;
    $('sourceLabel').textContent = `FROZEN CASE · ${sourceSnapshotDate} · ${evidenceWindow} · LEVEL ${scenario.level}`;
    setButtons(false);
    movePlayer(state.player);
  };
  const tick = () => {
    if (state.paused || state.completion) return;
    state.elapsedSeconds += 1;
    state.turnSeconds += 1;
    $('timer').textContent = format(state.elapsedSeconds);
    const remaining = scenario.graceSeconds - state.turnSeconds;
    $('grace').textContent = remaining > 0 ? `${remaining}s` : `+${Math.max(0, state.turnSeconds - scenario.graceSeconds) * 10}`;
    save();
  };
  const choose = playerAction => {
    const step = scenario.steps[state.index];
    if (!step || buttons().every(button => button.disabled)) return;
    const mimicPenalty = actionPenalty(step.strategyAction, playerAction);
    const delayPenalty = timePenalty(state.turnSeconds);
    const totalPenalty = mimicPenalty + delayPenalty;
    state.penaltyPoints += totalPenalty;
    state.gamePoints = state.penaltyPoints;
    state.choices.push({ time:step.time, title:step.title, playerAction, strategyAction:step.strategyAction, mimicPenalty, delayPenalty, totalPenalty, outcome:step.outcome, closeType:step.closeType, at:state.elapsedSeconds });
    setButtons(true);
    const selected = document.querySelector(`[data-action="${playerAction}"]`);
    if (selected) selected.classList.add('selected');
    movePlayer(nodeGraph[playerAction]);
    $('penalty').textContent = state.penaltyPoints;
    $('missionBadge').textContent = totalPenalty === 0 ? 'ROUTE ALIGNED' : 'ROUTE DRIFT';
    const timeLine = delayPenalty ? ` · time +${delayPenalty}` : '';
    $('feedback').textContent = `Your action: ${playerAction} · strategy route: ${step.strategyAction} · ${step.outcome} · penalty +${mimicPenalty}${timeLine}`;
    $('feedback').className = `feedback ${totalPenalty === 0 ? 'good' : 'bad'}`;
    $('continueGame').textContent = state.index === scenario.steps.length - 1 ? 'SEE MIMIC RESULT →' : 'NEXT MOMENT →';
    $('continueGame').hidden = false;
    save();
  };
  const finish = () => {
    state.completion = true;
    clearInterval(state.timer);
    $('game').hidden = true;
    $('result').hidden = false;
    const zeroMoves = state.choices.filter(choice => choice.totalPenalty === 0).length;
    $('resultTitle').textContent = state.penaltyPoints === 0 ? 'Perfect strategy echo' : 'Route replay complete';
    $('resultCopy').textContent = state.penaltyPoints === 0 ? 'You mirrored every recorded strategy action inside the free decision time.' : 'Replay the route to see where action distance or delayed choices added penalty.';
    $('finalPoints').textContent = state.penaltyPoints;
    $('finalTime').textContent = format(state.elapsedSeconds);
    $('routeScore').textContent = `${zeroMoves} / ${scenario.steps.length}`;
    save();
  };
  const replay = () => {
    $('replayPanel').hidden = false;
    $('replaySteps').innerHTML = state.choices.map((choice,index) => `<article class="replay-step ${choice.totalPenalty === 0 ? 'good' : 'bad'}"><small>MOVE ${index + 1} · ${choice.time} · ${format(choice.at)}</small><b>YOU ${choice.playerAction} · STRATEGY ${choice.strategyAction}</b><p>${choice.outcome} · mimic +${choice.mimicPenalty} · time +${choice.delayPenalty} · total +${choice.totalPenalty}</p></article>`).join('');
    $('replayPanel').scrollIntoView({behavior:'smooth'});
  };
  $('startGame').onclick = () => { reset(); $('intro').hidden = true; $('game').hidden = false; state.timer = setInterval(tick,1000); render(); };
  $('continueGame').onclick = () => { state.index += 1; render(); };
  buttons().forEach(button => { button.onclick = () => choose(button.dataset.action); });
  $('pauseGame').onclick = () => { state.paused = !state.paused; $('pauseGame').textContent = state.paused ? '▶' : 'Ⅱ'; $('missionBadge').textContent = state.paused ? 'PAUSED' : 'MIMIC THE ROUTE'; save(); };
  $('restartGame').onclick = () => { reset(); $('result').hidden = true; $('replayPanel').hidden = true; $('intro').hidden = false; };
  $('replayGame').onclick = replay;
})();
