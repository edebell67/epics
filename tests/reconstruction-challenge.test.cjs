const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', 'ep_054_strategy_reconstruction_challenge');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

test('Level 1 strategy-mimic challenge provides a mobile game shell and clear historical boundary', () => {
  const html = read('index.html');
  assert.match(html, /Historical Strategy Mimic/i);
  assert.match(html, /historical strategy-mimic game/i);
  assert.match(html, /id="startGame"/);
  assert.match(html, /id="pauseGame"/);
  assert.match(html, /id="choiceGrid"/);
  assert.match(html, /id="gameMap"/);
  assert.match(html, /id="replayPanel"/);
  assert.match(html, /class="game-title"/);
  assert.match(html, /id="missionBadge"/);
  assert.match(html, /id="playerToken"/);
  assert.match(html, /id="caseObjective"/);
  assert.match(html, /id="continueGame"/);
  assert.match(html, /id="penalty"/);
  assert.match(html, /class="[^\"]*game-board/);
  assert.match(html, /not investment advice/i);
  assert.match(html, /meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/);
});

test('scenario code locks a dated source snapshot and records game-only penalty, time, choices and replay', () => {
  const js = read('game.js');
  assert.match(js, /sourceSnapshotDate/);
  assert.match(js, /evidenceWindow/);
  assert.match(js, /gamePoints/);
  assert.match(js, /penaltyPoints/);
  assert.match(js, /nodeGraph/);
  assert.match(js, /movePlayer/);
  assert.match(js, /continueGame/);
  assert.match(js, /elapsedSeconds/);
  assert.match(js, /choices/);
  assert.match(js, /pause/);
  assert.match(js, /replay/);
  assert.match(js, /completion/);
  assert.doesNotMatch(js, /brokerage|order submission|trade execution/i);
});

test('mobile-first CSS exposes full-width decision controls and reduced-motion support', () => {
  const css = read('game.css');
  assert.match(css, /min-height:\s*48px/);
  assert.match(css, /--void:/);
  assert.match(css, /\.game-board/);
  assert.match(css, /\.player-token/);
  assert.match(css, /@keyframes/);
  assert.match(css, /@media \(prefers-reduced-motion:\s*reduce\)/);
  assert.match(css, /@media \(min-width:\s*760px\)/);
});

test('strategy-mimic play uses B/S/H actions with low-is-best penalties and shrinking decision grace', () => {
  const html = read('index.html');
  const js = read('game.js');
  assert.match(html, /data-action="B"/);
  assert.match(html, /data-action="S"/);
  assert.match(html, /data-action="H"/);
  assert.match(html, /id="penalty"/);
  assert.match(js, /strategyAction/);
  assert.match(js, /actionPenalty/);
  assert.match(js, /graceSeconds/);
  assert.match(js, /\[10,\s*5,\s*3\]/);
  assert.match(js, /same action[^\n]*0 penalty/i);
  assert.match(js, /per second/i);
  assert.doesNotMatch(js, /correct\s*\?/i);
});
