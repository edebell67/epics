const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const source = (file) => fs.readFileSync(path.join(root, file), 'utf8');

test('waitlist page captures consent and the source of every lead', () => {
  const html = source('index.html');
  const js = source('waitlist.js');

  for (const token of ['id="waitlistForm"', 'name="email"', 'name="discoverySource"', 'name="consent"', 'name="company"']) {
    assert.match(html, new RegExp(token));
  }
  assert.match(html, /Strategy Directory app/);
  assert.match(html, /Agentic Trading Arena/);
  assert.match(html, /Strategy Directory and Agentic Trading Arena waitlist updates/);
  assert.match(html, /Join the waitlist/i);
  assert.match(js, /https:\/\/ep052-agentic-arena\.onrender\.com\/api\/waitlist/);
  assert.match(js, /URLSearchParams/);
  assert.match(js, /document\.referrer/);
});
