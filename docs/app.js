const sampleContacts = [
  { id: 'sample-001', label: 'Sample recipient 01', first_name: 'Ari', course: 'Python basics', consent: true, opt_out: false },
  { id: 'sample-002', label: 'Sample recipient 02', first_name: 'Bea', course: 'Data foundations', consent: false, opt_out: false },
  { id: 'sample-003', label: 'Sample recipient 03', first_name: 'Cal', course: 'Web design', consent: true, opt_out: true },
  { id: 'sample-004', label: 'Sample recipient 04', first_name: 'Dina', course: 'Secure coding', consent: true, opt_out: false },
  { id: 'sample-001', label: 'Duplicate sample row', first_name: 'Ari', course: 'Python basics', consent: true, opt_out: false }
];
const defaultTemplate = 'Hi {{first_name}}, your {{course}} sample reminder is ready.';
const MAX_CSV_BYTES = 1_048_576;
const MAX_RECIPIENTS = 1_000;
function parseCsv(text) {
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > MAX_CSV_BYTES) throw new Error('Choose a CSV file smaller than 1 MiB.');
  const rows = []; let row = [], value = '', quoted = false, afterQuote = false, atStart = true;
  const pushRow = () => { row.push(value); if (row.some(cell => cell !== '')) rows.push(row); row = []; value = ''; afterQuote = false; atStart = true; if (rows.length > MAX_RECIPIENTS + 1) throw new Error('The CSV can contain at most 1,000 recipient rows.'); };
  text = text.replace(/^\uFEFF/, '');
  if (!text.trim()) throw new Error('The CSV file is empty.');
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) { if (char === '"' && text[i + 1] === '"') { value += '"'; i++; } else if (char === '"') { quoted = false; afterQuote = true; } else value += char; continue; }
    if (afterQuote && char !== ',' && char !== '\n' && char !== '\r') throw new Error('The CSV has characters after a closing quote.');
    if (char === '"') { if (!atStart) throw new Error('The CSV contains a quote outside a quoted field.'); quoted = true; atStart = false; }
    else if (char === ',') { row.push(value); value = ''; afterQuote = false; atStart = true; }
    else if (char === '\n' || char === '\r') { if (char === '\r' && text[i + 1] === '\n') i++; pushRow(); }
    else { value += char; atStart = false; }
  }
  if (quoted) throw new Error('The CSV contains an unclosed quoted field.');
  if (value !== '' || row.length) pushRow();
  if (rows.length < 2) throw new Error('Add a header row and at least one recipient.');
  const headers = rows.shift().map(header => header.trim());
  if (new Set(headers).size !== headers.length) throw new Error('Duplicate CSV column names are not supported.');
  if (headers.some(header => /phone|mobile|telephone|msisdn|number/i.test(header))) throw new Error('Do not include phone-number columns; this planner never processes recipient numbers.');
  const required = ['id', 'first_name', 'course', 'consent', 'opt_out'];
  if (required.some(header => !headers.includes(header))) throw new Error('Required columns: id, first_name, course, consent, opt_out.');
  const booleanValue = (raw, rowNumber, field) => {
    const token = raw.trim().toLowerCase();
    if (['true', 'yes', '1'].includes(token)) return true;
    if (['false', 'no', '0'].includes(token)) return false;
    throw new Error(`Row ${rowNumber}: ${field} must be true/false, yes/no, or 1/0.`);
  };
  return rows.map((cells, index) => {
    if (cells.length > headers.length && cells.slice(headers.length).some(cell => cell !== '')) throw new Error(`Row ${index + 2} has more values than the header.`);
    const item = Object.fromEntries(headers.map((header, i) => [header, cells[i] ?? '']));
    if (Object.values(item).some(cell => cell.length > 256)) throw new Error(`Row ${index + 2} contains a field longer than 256 characters.`);
    if (!item.id.trim()) throw new Error(`Row ${index + 2}: id cannot be empty.`);
    return { id: item.id.trim(), label: item.first_name.trim() || `Recipient row ${index + 2}`, first_name: item.first_name.trim(), course: item.course.trim(), consent: booleanValue(item.consent, index + 2, 'consent'), opt_out: booleanValue(item.opt_out, index + 2, 'opt_out') };
  });
}
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
  return { errors: queued ? [] : ['No eligible recipients remain after consent and opt-out checks.'], rows, summary: { total: contacts.length, queued, excluded: contacts.length - queued, duplicates, costUnits: queued } };
}
function csvCell(value) { let text = String(value ?? ''); if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`; return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text; }
function buildPlanCsv(rows) {
  const header = ['id', 'first_name', 'course', 'consent', 'opt_out', 'decision', 'message_preview'];
  return `\uFEFF${[header, ...rows.map(row => [row.id, row.first_name, row.course, row.consent, row.opt_out, row.decision, row.preview])].map(line => line.map(csvCell).join(',')).join('\r\n')}\r\n`;
}
if (typeof module !== 'undefined') module.exports = { sampleContacts, defaultTemplate, validateTemplate, personalize, dryRun, parseCsv, buildPlanCsv };
if (typeof document !== 'undefined') {
  const message = document.querySelector('#message'), results = document.querySelector('#results'), errors = document.querySelector('#errors'), empty = document.querySelector('#empty'), run = document.querySelector('#run');
  const file = document.querySelector('#contacts-file'), processFile = document.querySelector('#process-file'), exportButton = document.querySelector('#export-plan');
  let importedContacts = null, planRows = [];
  function render(result) {
    planRows = result.rows;
    exportButton.disabled = planRows.length === 0;
    errors.hidden = result.errors.length === 0; errors.textContent = result.errors.join(' '); empty.hidden = result.rows.length > 0;
    results.replaceChildren(...result.rows.map(row => {
      const tr = document.createElement('tr'), name = document.createElement('td'), consent = document.createElement('td'), preview = document.createElement('td'), decision = document.createElement('td');
      name.className = 'recipient'; name.textContent = row.label; const sub = document.createElement('small'); sub.textContent = `Consent: ${row.consent ? 'recorded in sample' : 'missing'} · Opt-out: ${row.opt_out ? 'yes' : 'no'}`; name.append(sub);
      consent.textContent = row.consent ? 'Recorded' : 'Missing'; consent.className = row.consent ? '' : 'muted'; preview.className = 'preview'; preview.textContent = row.preview || 'Not prepared';
      const badge = document.createElement('span'); badge.className = `decision ${row.decision.startsWith('Queued') ? 'queued' : 'excluded'}`; badge.textContent = row.decision; decision.append(badge); tr.append(name, consent, preview, decision); return tr;
    }));
    for (const [id, value] of [['total', result.summary.total], ['queued', result.summary.queued], ['excluded', result.summary.excluded], ['duplicates', result.summary.duplicates], ['cost', `${result.summary.costUnits} units`]]) document.querySelector(`#metric-${id}`).textContent = value;
    document.querySelector('#status').textContent = result.errors.length ? 'Review the validation note before preparing a preview' : `Dry run complete · ${result.summary.queued} message previews prepared locally`;
  }
  function updateCounter() { document.querySelector('#counter').textContent = `${message.value.length} / 160`; document.querySelector('#counter').classList.toggle('over', message.value.length > 160); }
  message.addEventListener('input', updateCounter);
  run.addEventListener('click', () => render(dryRun(sampleContacts, message.value)));
  processFile.addEventListener('click', () => { if (importedContacts) render(dryRun(importedContacts, message.value)); });
  file.addEventListener('change', async () => {
    importedContacts = null; processFile.disabled = true; exportButton.disabled = true; planRows = [];
    errors.hidden = true; errors.textContent = ''; results.replaceChildren(); empty.hidden = true;
    for (const id of ['total', 'queued', 'excluded', 'duplicates', 'cost']) document.querySelector(`#metric-${id}`).textContent = '—';
    const chosen = file.files?.[0];
    if (!chosen) return;
    if (chosen.size > MAX_CSV_BYTES) { errors.textContent = 'Choose a CSV file smaller than 1 MiB.'; errors.hidden = false; document.querySelector('#status').textContent = 'File rejected · size limit'; return; }
    document.querySelector('#status').textContent = 'Reading the selected CSV in this tab…';
    try { importedContacts = parseCsv(await chosen.text()); processFile.disabled = false; document.querySelector('#status').textContent = `Loaded ${importedContacts.length} rows in this tab · ready for dry run`; }
    catch (error) { importedContacts = null; errors.textContent = error instanceof Error ? error.message : 'The CSV could not be read.'; errors.hidden = false; document.querySelector('#status').textContent = 'File not processed'; }
  });
  exportButton.addEventListener('click', () => {
    if (!planRows.length) return;
    const blob = new Blob([buildPlanCsv(planRows)], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'campaign-dry-run.csv'; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 0);
  });
  document.querySelector('#reset').addEventListener('click', () => { message.value = defaultTemplate; file.value = ''; importedContacts = null; processFile.disabled = true; exportButton.disabled = true; planRows = []; updateCounter(); results.replaceChildren(); errors.hidden = true; errors.textContent = ''; empty.hidden = true; for (const id of ['total', 'queued', 'excluded', 'duplicates', 'cost']) document.querySelector(`#metric-${id}`).textContent = '—'; document.querySelector('#status').textContent = 'Ready · no messages have been prepared'; message.focus(); });
  updateCounter();
}
