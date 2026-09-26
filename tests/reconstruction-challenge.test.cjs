const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', 'ep_054_strategy_reconstruction_challenge');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

test('Level 1 reconstruction challenge provides a mobile game shell and clear historical boundary', () => {
  const html = read('index.html');
  assert.match(html, /Historical Strategy Reconstruction Challenge/i);
  assert.match(html, /historical reconstruction game/i);
  assert.match(html, /id="startGame"/);
  assert.match(html, /id="pauseGame"/);
  assert.match(html, /id="choiceGrid"/);
  assert.match(html, /id="gameMap"/);
  assert.match(html, /id="replayPanel"/);
  assert.match(html, /not investment advice/i);
  assert.match(html, /meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/);
});

test('scenario code locks a dated source snapshot and records game-only score, time, choices and replay', () => {
  const js = read('game.js');
  assert.match(js, /sourceSnapshotDate/);
  assert.match(js, /evidenceWindow/);
  assert.match(js, /gamePoints/);
  assert.match(js, /elapsedSeconds/);
  assert.match(js, /choices/);
  assert.match(js, /pause/);
  assert.match(js, /replay/);
  assert.match(js, /completion/);
  assert.doesNotMatch(js, /brokerage|order submission|trade execution/i);
});

test('mobile-first CSS exposes full-width decision controls and reduced-motion support', () => {
  const css = read('game.css');
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /@media \(min-width: 760px\)/);
});
