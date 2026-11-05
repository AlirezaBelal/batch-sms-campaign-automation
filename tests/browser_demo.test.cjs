const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { sampleContacts, defaultTemplate, validateTemplate, personalize, dryRun, parseCsv, buildPlanCsv } = require('../docs/app.js');

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

test('local consent ledger validates booleans, limits and forbidden phone columns', () => {
  const csv = '\uFEFFid,first_name,course,consent,opt_out\r\na-1,Ari,Python,true,false\r\na-1,Bea,Design,yes,no\r\na-3,Cal,Web,no,false\r\n';
  const rows = parseCsv(csv);
  const result = dryRun(rows, defaultTemplate);
  assert.deepEqual(result.summary, { total: 3, queued: 1, excluded: 2, duplicates: 1, costUnits: 1 });
  assert.equal(result.rows[0].preview, 'Hi Ari, your Python sample reminder is ready.');
  assert.throws(() => parseCsv(csv.replace(',opt_out', ',phone_number,opt_out').replace('true,false', 'true,09121234567,false')), /never processes recipient numbers/);
  assert.throws(() => parseCsv(csv.replace('true,false', 'maybe,false')), /must be true\/false/);
  assert.throws(() => parseCsv('id,first_name,course,consent,opt_out\na,Ari,Python,true,false\n'.repeat(1002)), /1,000/);
});

test('exported plans neutralize spreadsheet formulas', () => {
  const plan = buildPlanCsv([{ id: '=1+1', first_name: '+Ari', course: 'Python', consent: true, opt_out: false, decision: 'Queued in dry run', preview: '@SUM(1,2)' }]);
  assert.match(plan, /'=1\+1,'\+Ari/);
  assert.match(plan, /"'@SUM\(1,2\)"/);
});

test('public demo has no gateway, phone entry, or outbound connection', () => {
  const page = fs.readFileSync('docs/index.html', 'utf8');
  const app = fs.readFileSync('docs/app.js', 'utf8');
  assert.match(page, /connect-src 'none'/);
  assert.match(page, /type="file"[^>]+accept="\.csv,text\/csv"/);
  assert.doesNotMatch(page, /type=["'](?:text|tel|number)["']/i);
  assert.doesNotMatch(app, /fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|localStorage/);
});
