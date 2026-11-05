const sampleContacts = [
  { id: 'sample-001', label: 'Sample recipient 01', first_name: 'Ari', course: 'Python basics', consent: true, opt_out: false },
  { id: 'sample-002', label: 'Sample recipient 02', first_name: 'Bea', course: 'Data foundations', consent: false, opt_out: false },
  { id: 'sample-003', label: 'Sample recipient 03', first_name: 'Cal', course: 'Web design', consent: true, opt_out: true },
  { id: 'sample-004', label: 'Sample recipient 04', first_name: 'Dina', course: 'Secure coding', consent: true, opt_out: false },
  { id: 'sample-001', label: 'Duplicate sample row', first_name: 'Ari', course: 'Python basics', consent: true, opt_out: false }
];
const defaultTemplate = 'Hi {{first_name}}, your {{course}} sample reminder is ready.';
function validateTemplate(template) {
  const text = String(template ?? '');
  if (!text.trim()) return ['Message template is required.'];
  if (text.length > 160) return ['Message template exceeds the 160-character dry-run limit.'];
  const tokens = [...text.matchAll(/{{\s*([a-z_]+)\s*}}/g)].map(match => match[1]);
  const remainder = text.replace(/{{\s*[a-z_]+\s*}}/g, '');
  const leftovers = remainder.includes('{{') || remainder.includes('}}');
  if (leftovers) return ['A personalization token is malformed. Use {{first_name}} or {{course}}.'];
  const unknown = tokens.find(token => !['first_name', 'course'].includes(token));
  return unknown ? [`Unsupported personalization token: {{${unknown}}}.`] : [];
}
function personalize(template, contact) {
  return template.replace(/{{\s*(first_name|course)\s*}}/g, (_, key) => String(contact[key] || ''));
}
function dryRun(contacts, template) {
  const errors = validateTemplate(template);
  if (errors.length) return { errors, rows: [], summary: { total: contacts.length, queued: 0, excluded: contacts.length, duplicates: 0, costUnits: 0 } };
  const seen = new Set(), rows = [], optOutIds = new Set(contacts.filter(c => c.opt_out).map(c => c.id));
  let duplicates = 0, queued = 0;
  for (const contact of contacts) {
    let decision;
    if (optOutIds.has(contact.id)) decision = 'Excluded · opted out';
    else if (!contact.consent) decision = 'Excluded · no consent';
    else if (seen.has(contact.id)) { decision = 'Excluded · duplicate'; duplicates++; }
    else { decision = 'Queued in dry run'; seen.add(contact.id); queued++; }
    rows.push({ ...contact, decision, preview: decision === 'Queued in dry run' ? personalize(template, contact) : '' });
  }
  return { errors: queued ? [] : ['No eligible sample recipients remain after consent and opt-out checks.'], rows, summary: { total: contacts.length, queued, excluded: contacts.length - queued, duplicates, costUnits: queued } };
}
if (typeof module !== 'undefined') module.exports = { sampleContacts, defaultTemplate, validateTemplate, personalize, dryRun };
if (typeof document !== 'undefined') {
  const message = document.querySelector('#message'), results = document.querySelector('#results'), errors = document.querySelector('#errors'), empty = document.querySelector('#empty'), run = document.querySelector('#run');
  function render(result) {
    errors.hidden = result.errors.length === 0; errors.textContent = result.errors.join(' '); empty.hidden = result.rows.length > 0;
    results.replaceChildren(...result.rows.map(row => {
      const tr = document.createElement('tr'), name = document.createElement('td'), consent = document.createElement('td'), preview = document.createElement('td'), decision = document.createElement('td');
      name.className = 'recipient'; name.textContent = row.label; const sub = document.createElement('small'); sub.textContent = `Consent: ${row.consent ? 'recorded in sample' : 'missing'} · Opt-out: ${row.opt_out ? 'yes' : 'no'}`; name.append(sub);
      consent.textContent = row.consent ? 'Recorded' : 'Missing'; consent.className = row.consent ? '' : 'muted'; preview.className = 'preview'; preview.textContent = row.preview || 'Not prepared';
      const badge = document.createElement('span'); badge.className = `decision ${row.decision.startsWith('Queued') ? 'queued' : 'excluded'}`; badge.textContent = row.decision; decision.append(badge); tr.append(name, consent, preview, decision); return tr;
    }));
    for (const [id, value] of [['total', result.summary.total], ['queued', result.summary.queued], ['excluded', result.summary.excluded], ['duplicates', result.summary.duplicates], ['cost', `${result.summary.costUnits} units`]]) document.querySelector(`#metric-${id}`).textContent = value;
    document.querySelector('#status').textContent = result.errors.length ? 'Review the validation note before preparing a preview' : `Dry run complete · ${result.summary.queued} sample messages prepared locally`;
  }
  function updateCounter() { document.querySelector('#counter').textContent = `${message.value.length} / 160`; document.querySelector('#counter').classList.toggle('over', message.value.length > 160); }
  message.addEventListener('input', updateCounter);
  run.addEventListener('click', () => render(dryRun(sampleContacts, message.value)));
  document.querySelector('#reset').addEventListener('click', () => { message.value = defaultTemplate; updateCounter(); results.replaceChildren(); errors.hidden = true; errors.textContent = ''; empty.hidden = true; for (const id of ['total', 'queued', 'excluded', 'duplicates', 'cost']) document.querySelector(`#metric-${id}`).textContent = '—'; document.querySelector('#status').textContent = 'Ready · no messages have been prepared'; message.focus(); });
  updateCounter();
}

