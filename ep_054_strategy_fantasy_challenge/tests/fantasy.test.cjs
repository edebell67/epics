/* Version history
 * v1.3.0 · 2026-08-31 · Verifies MVP 1 attributable friend invitations.
 * v1.2.0 · 2026-08-31 · Verifies the ruthlessly small Global Challenge MVP.
 * v1.0.0 · 2026-08-31 · Version history added; file predates this convention.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const source = name => fs.readFileSync(path.join(root, name), 'utf8');

test('MVP exposes one launch loop', () => {
  const html=source('index.html');
  for(const token of ['Build your portfolio','CHOOSE 3–10','Enter Global Challenge','Your nearest rivals','Challenge a friend']) assert.match(html,new RegExp(token));
  for(const id of ['portfolioName','portfolioStrategies','addStrategy','enterGlobal','neighbourRows','challengeFriend','inviteDialog']) assert.match(html,new RegExp(`id="${id}"`));
});

test('MVP defers non-launch features', () => {
  const html=source('index.html');
  assert.match(html,/Separate private competitions, monitoring, portfolio reuse and agent hand-off belong to future versions/);
  assert.doesNotMatch(html,/id="sendToAgent"/);
  assert.doesNotMatch(html,/id="createChallenge"/);
});

test('portfolio selection is capped at ten', () => {
  const html=source('index.html'), js=source('fantasy.js');
  assert.match(js,/state\.strategies\.length<10/);
  assert.match(js,/state\.strategies\.length>=10/);
  assert.match(html,/id="strategySearch"/);
  assert.match(html,/id="strategySort"/);
  assert.match(js,/win rate/);
  assert.match(js,/state\.strategies=\[\]/);
});

test('entered portfolio refreshes from server rankings and can be shared', () => {
  const html=source('index.html'), js=source('fantasy.js'), css=source('fantasy.css');
  assert.match(js,/setInterval\(\(\)=>advance/);
  assert.match(js,/15000/);
  assert.match(js,/\/api\/leaderboard/);
  assert.match(js,/\/api\/strategies/);
  assert.match(js,/getBoundingClientRect/);
  assert.match(js,/navigator\.share/);
  assert.match(css,/\.neighbour-row/);
  assert.match(css,/transition: transform/);
  assert.match(html,/EP051 EVIDENCE RANKING/);
  assert.doesNotMatch(js,/INV_\$\{hash\}/);
});

test('MVP 1 invitation is attributable and joins the same Global Challenge', () => {
  const html=source('index.html'), js=source('fantasy.js');
  for(const token of ['INVITE_CREATED','INVITE_SHARED','INVITE_OPENED','INVITE_ACCEPTED']) assert.match(js,new RegExp(token));
  assert.match(source('server.py'),/GLOBAL_WEEKLY/);
  assert.match(js,/\/invite\/\$\{state\.invite\.id\}/);
  assert.match(html,/SAME GLOBAL CHALLENGE/);
  assert.match(html,/id="friendPreview"/);
});

test('preview is mobile-first and declares the real-data boundary', () => {
  const html=source('index.html'), css=source('fantasy.css'), server=source('server.py');
  assert.match(html,/viewport-fit=cover/);
  assert.match(html,/use EP051 Strategy Directory evidence/);
  assert.match(css,/@media \(min-width: 768px\)/);
  assert.match(server,/FastAPI/);
});
