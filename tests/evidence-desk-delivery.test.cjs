const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('Evidence Desk has a concrete public sample delivery with scope, source, record, finding and limits', () => {
  const html = read('research/dna-evidence-access/sample-delivery/index.html');
  assert.match(html, /DNA Evidence Desk/i);
  assert.match(html, /Action Trace Review/i);
  assert.match(html, /DNA_200651/);
  assert.match(html, /23 September 2026/);
  assert.match(html, /01:39/);
  assert.match(html, /02:23/);
  assert.match(html, /04:30/);
  assert.match(html, /07:59/);
  assert.match(html, /Scope/);
  assert.match(html, /Finding/);
  assert.match(html, /Limitations/);
  assert.match(html, /not investment advice/i);
});

test('Evidence Desk landing page links the concrete sample delivery', () => {
  const landing = read('research/dna-evidence-access/index.html');
  assert.match(landing, /sample-delivery\//);
  assert.match(landing, /Open an actual sample delivery/i);
});
