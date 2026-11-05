const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { sampleContacts, defaultTemplate, validateTemplate, personalize, dryRun } = require('../docs/app.js');

test('template personalization uses only the fixed safe tokens', () => {
  assert.equal(personalize(defaultTemplate, sampleContacts[0]), 'Hi Ari, your Python basics sample reminder is ready.');
  assert.deepEqual(validateTemplate('Hi {{first_name}}'), []);
  assert.match(validateTemplate('Hi {{phone}}')[0], /Unsupported/);
  assert.match(validateTemplate('Hi {{first_name')[0], /malformed/);
  assert.match(validateTemplate('x'.repeat(161))[0], /160-character/);
});

test('dry run enforces consent, opt-outs, and duplicate suppression', () => {
  const result = dryRun(sampleContacts, defaultTemplate);
  assert.deepEqual(result.summary, { total: 5, queued: 2, excluded: 3, duplicates: 1, costUnits: 2 });
  assert.deepEqual(result.rows.map(x => x.decision), ['Queued in dry run', 'Excluded · no consent', 'Excluded · opted out', 'Queued in dry run', 'Excluded · duplicate']);
  assert.equal(result.rows[0].preview, 'Hi Ari, your Python basics sample reminder is ready.');
});

test('no message is queued when no sample recipient is eligible', () => {
  const result = dryRun(sampleContacts.map(contact => ({ ...contact, consent: false })), defaultTemplate);
  assert.equal(result.summary.queued, 0);
  assert.match(result.errors[0], /No eligible/);
});

test('public demo has no gateway, phone entry, or outbound connection', () => {
  const page = fs.readFileSync('docs/index.html', 'utf8');
  const app = fs.readFileSync('docs/app.js', 'utf8');
  assert.match(page, /connect-src 'none'/);
  assert.doesNotMatch(page, /type=["']file|<input\b/i);
  assert.doesNotMatch(app, /fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|localStorage/);
});

