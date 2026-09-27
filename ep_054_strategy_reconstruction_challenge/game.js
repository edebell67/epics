(() => {
  'use strict';

  // Free seconds before the time penalty starts, indexed by game/level (1st..5th); level 6+ gets 0s (penalty starts immediately on load).
  const graceSchedule = [10, 5, 3, 2, 1];
  const graceForLevel = level => graceSchedule[level - 1] ?? 0;
  // Move count grows +2 per level: level 1 = 4 moves, level 2 = 6, level 3 = 8, etc.
  // Each level's steps must come from a real frozen trade record before it's added below.
  const movesForLevel = level => 4 + (level - 1) * 2;
  const stepTitles = ['Opening signal', 'First reversal', 'Return to route', 'Second reversal'];
  // Every case below is a real, frozen closed-trade sequence read from the local EP058
  // PostgreSQL tradedb (combined_trades_closed), one model/product/day per case. A new
  // game picks a different case than the last one played, so replays don't repeat.
  const caseLibrary = [
    {
      id: 'HSM-001', model: 'DNA_200651', asset: 'CHF', dateLabel: '2026-09-23', level: 1,
      steps: [
        { time:'01:39', strategyAction:'B', pnl:70, position:'flat position', tp:100, sl:-30 },
        { time:'02:23', strategyAction:'S', pnl:-40, position:'previous BUY closed +70', tp:100, sl:-30 },
        { time:'04:30', strategyAction:'B', pnl:85, position:'previous SELL closed −40', tp:100, sl:-30 },
        { time:'07:59', strategyAction:'S', pnl:-40, position:'previous BUY closed +85', tp:100, sl:-30 }
      ]
    },
    {
      id: 'HSM-002', model: 'DNA_200018', asset: 'AUD', dateLabel: '2026-09-24', level: 1,
      steps: [
        { time:'00:52', strategyAction:'S', pnl:215, position:'flat position', tp:200, sl:-200 },
        { time:'16:21', strategyAction:'S', pnl:-225, position:'previous SELL closed +215', tp:200, sl:-200 },
        { time:'17:51', strategyAction:'S', pnl:145, position:'previous SELL closed −225', tp:200, sl:-200 },
        { time:'22:16', strategyAction:'B', pnl:-50, position:'previous SELL closed +145', tp:200, sl:-200 }
      ]
    },
    {
      id: 'HSM-003', model: 'DNA_202273', asset: 'NZD', dateLabel: '2026-09-24', level: 1,
      steps: [
        { time:'01:07', strategyAction:'B', pnl:-60, position:'flat position', tp:100, sl:-200 },
        { time:'16:05', strategyAction:'B', pnl:195, position:'previous BUY closed −60', tp:100, sl:-200 },
        { time:'18:17', strategyAction:'B', pnl:-65, position:'previous BUY closed +195', tp:100, sl:-200 },
        { time:'22:58', strategyAction:'S', pnl:-20, position:'previous BUY closed −65', tp:100, sl:-200 }
      ]
    }
  ];
  caseLibrary.forEach(c => c.steps.forEach((step, i) => { step.title = stepTitles[i] || `Moment ${i + 1}`; step.prompt = 'What action does the strategy take?'; }));
  caseLibrary.forEach(c => console.assert(c.steps.length === movesForLevel(c.level), `${c.id}: level ${c.level} should have ${movesForLevel(c.level)} moves, has ${c.steps.length}`));
  const lastCaseKey = 'hsm-last-case';
  const pickCase = () => {
    const lastId = localStorage.getItem(lastCaseKey);
    const pool = caseLibrary.filter(c => c.id !== lastId);
    const chosen = (pool.length ? pool : caseLibrary)[Math.floor(Math.random() * (pool.length ? pool.length : caseLibrary.length))];
    localStorage.setItem(lastCaseKey, chosen.id);
    return chosen;
  };
  let scenario = null;
  const outcomeText = pnl => `${pnl > 0 ? '+' : ''}${pnl} historical result`;
  const marketClue = step => `${scenario.asset} · ${step.position} · TP +${step.tp} · SL ${step.sl}`;
  const toSeconds = time => { const [m, s] = time.split(':').map(Number); return m * 60 + s; };
  const recentWindowSeconds = 5 * 60;
  // Rolling "last 5 min" activity clue, computed from the real frozen timestamps/outcomes of trades
  // that already closed before this moment — not a running total since the game started.
  const statsClue = index => {
    const now = toSeconds(scenario.steps[index].time);
    const recent = scenario.steps.slice(0, index).filter(s => now - toSeconds(s.time) <= recentWindowSeconds);
    const buys = recent.filter(s => s.strategyAction === 'B').length;
    const sells = recent.filter(s => s.strategyAction === 'S').length;
    const closed = recent.length;
    const profit = recent.filter(s => s.pnl > 0).length;
    if (!closed) return 'last 5 min: no closed trades yet';
    return `last 5 min: ${buys} buy${buys === 1 ? '' : 's'} · ${sells} sell${sells === 1 ? '' : 's'} · ${closed} closed · ${profit} profit`;
  };
  const state = { index:0, gamePoints:0, penaltyPoints:0, elapsedSeconds:0, turnSeconds:0, paused:false, choices:[], completion:false, timer:null, advanceTimer:null, pendingAdvance:false };
  const $ = id => document.getElementById(id);
  const format = total => `${String(Math.floor(total / 60)).padStart(2,'0')}:${String(total % 60).padStart(2,'0')}`;
  const save = () => localStorage.setItem('hsm-001', JSON.stringify({...state, timer:null, advanceTimer:null}));
  const reset = () => { clearInterval(state.timer); clearTimeout(state.advanceTimer); Object.assign(state,{index:0,gamePoints:0,penaltyPoints:0,elapsedSeconds:0,turnSeconds:0,paused:false,choices:[],completion:false,timer:null,advanceTimer:null,pendingAdvance:false}); localStorage.removeItem('hsm-001'); };
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
    $('context').innerHTML = `<div class="clue-market">${marketClue(step)}</div><div class="clue-stats">${statsClue(state.index)}</div>`;
    $('missionBadge').textContent = 'MIMIC THE ROUTE';
    $('feedback').textContent = '';
    $('feedback').className = 'feedback';
    $('continueGame').hidden = true;
    $('sourceLabel').textContent = `FROZEN CASE · ${scenario.dateLabel} · ${scenario.model} · ${scenario.asset} · fixed completed trade record · LEVEL ${scenario.level}`;
    $('progressFill').style.width = `${(state.index / scenario.steps.length) * 100}%`;
    setButtons(false);
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
    state.choices.push({ time:step.time, title:step.title, playerAction, strategyAction:step.strategyAction, mimicPenalty, delayPenalty, totalPenalty, outcome:outcomeText(step.pnl), at:state.elapsedSeconds });
    setButtons(true);
    const selected = document.querySelector(`[data-action="${playerAction}"]`);
    if (selected) selected.classList.add('selected');
    $('penalty').textContent = state.penaltyPoints;
    $('missionBadge').textContent = totalPenalty === 0 ? 'ROUTE ALIGNED' : 'ROUTE DRIFT';
    const timeLine = delayPenalty ? ` · time +${delayPenalty}` : '';
    $('feedback').textContent = `Your action: ${playerAction} · strategy route: ${step.strategyAction} · ${outcomeText(step.pnl)} · penalty +${mimicPenalty}${timeLine}`;
    $('feedback').className = `feedback ${totalPenalty === 0 ? 'good' : 'bad'}`;
    save();
    clearTimeout(state.advanceTimer);
    state.advanceTimer = setTimeout(() => {
      if (state.paused) { state.pendingAdvance = true; return; }
      advance();
    }, 1100);
  };
  const advance = () => { state.pendingAdvance = false; state.index += 1; render(); };
  const finish = () => {
    state.completion = true;
    clearInterval(state.timer);
    clearTimeout(state.advanceTimer);
    $('game').hidden = true;
    $('result').hidden = false;
    const zeroMoves = state.choices.filter(choice => choice.totalPenalty === 0).length;
    $('resultTitle').textContent = state.penaltyPoints === 0 ? 'Perfect strategy echo' : 'Route replay complete';
    $('resultCopy').textContent = state.penaltyPoints === 0 ? 'You mirrored every recorded strategy action inside the free decision time.' : 'Replay the route to see where action distance or delayed choices added penalty.';
    $('finalPoints').textContent = state.penaltyPoints;
    $('finalTime').textContent = format(state.elapsedSeconds);
    $('routeScore').textContent = `${zeroMoves} / ${scenario.steps.length}`;
    $('progressFill').style.width = '100%';
    save();
  };
  const replay = () => {
    $('replayPanel').hidden = false;
    $('replaySteps').innerHTML = state.choices.map((choice,index) => `<article class="replay-step ${choice.totalPenalty === 0 ? 'good' : 'bad'}"><small>MOVE ${index + 1} · ${choice.time} · ${format(choice.at)}</small><b>YOU ${choice.playerAction} · STRATEGY ${choice.strategyAction}</b><p>${choice.outcome} · mimic +${choice.mimicPenalty} · time +${choice.delayPenalty} · total +${choice.totalPenalty}</p></article>`).join('');
    $('replaySource').textContent = `Source: fixed historical trade records for ${scenario.model}, ${scenario.asset}, ${scenario.dateLabel}, read from the local EP058 PostgreSQL tradedb API. Game data is frozen for this case.`;
    $('replayPanel').scrollIntoView({behavior:'smooth'});
  };
  $('startGame').onclick = () => {
    scenario = pickCase();
    scenario.graceSeconds = graceForLevel(scenario.level);
    reset();
    $('intro').hidden = true;
    $('game').hidden = false;
    state.timer = setInterval(tick, 1000);
    render();
  };
  buttons().forEach(button => { button.onclick = () => choose(button.dataset.action); });
  $('pauseGame').onclick = () => {
    state.paused = !state.paused;
    $('pauseGame').textContent = state.paused ? '▶' : 'Ⅱ';
    $('missionBadge').textContent = state.paused ? 'PAUSED' : 'MIMIC THE ROUTE';
    if (!state.paused && state.pendingAdvance) advance();
    save();
  };
  $('restartGame').onclick = () => { reset(); $('result').hidden = true; $('replayPanel').hidden = true; $('intro').hidden = false; };
  $('replayGame').onclick = replay;
})();
