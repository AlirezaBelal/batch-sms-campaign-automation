# Batch SMS Campaign Automation

[![CI](https://github.com/AlirezaBelal/batch-sms-campaign-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/AlirezaBelal/batch-sms-campaign-automation/actions/workflows/ci.yml)

A small Python CLI for previewing personalized, consent-based SMS campaigns and deliberately submitting them to **SMS Gateway for Android**. Dry Run is the default. Gateway acceptance is **not carrier delivery**.

## Quick start: no SMS, credentials or runtime network

Requires Python 3.10–3.14. Dependency installation needs package access; the installed demonstration runs offline.

```bash
git clone https://github.com/AlirezaBelal/batch-sms-campaign-automation.git
cd batch-sms-campaign-automation
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

No `.env` is required. Optional local configuration: copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`).

Output is two aggregate JSON lines: `preflight`, then `summary`. The bundled synthetic fixture produces:

```text
mode=dry_run, total_input=2, valid_records=2, eligible_recipients=2,
simulated=2, accepted_or_queued=0, invalid_records=0, exit_code=0
```

This is a readable extract, not the literal JSON. The example consent records are **fictional test assertions**. Never submit the example numbers. Live mode rejects the bundled filename and `demo` consent scope.

## Input and permission to send

CSV must be UTF-8 (BOM accepted), with distinct headers. Default name/phone columns are `first_name_per` and `selected_phone`; names may be empty. Supported mobile formats include `09…`, `9…`, `989…`, `+989…` and `00989…`, with Persian/Arabic digits and visual separators. Ambiguous numbers, embedded text, tabs/newlines and oversized phone fields are rejected rather than silently stripped.

Live eligibility additionally requires all of:

| Column | Required value |
|---|---|
| `consent_status` | `granted` |
| `consent_scope` | Exact match to the reviewed `SMS_CONSENT_SCOPE` |
| `consent_source` | Nonempty reference to the operator's evidence record, at most 128 characters |
| `consent_at` | ISO timestamp with timezone, not in the future |

These fields are **operator assertions**, not independent proof of lawful consent. Keep trustworthy evidence at its authorized source; do not copy private evidence into this repository. Missing, withdrawn, mismatched or incomplete assertions deny eligibility. Legacy two-column CSVs can be inspected in Dry Run but their records are ineligible.

Only use authorized recipients whose permission covers the actual message class. Purchased, scraped and unverified lists are prohibited. The optional upstream [Iran Contact Data Pipeline](https://github.com/AlirezaBelal/iran-contact-data-pipeline) can normalize data; it does **not** establish consent.

For Iranian recipients, review current [CRA guidance](https://www.cra.ir/), the [195 complaints service](https://195.cra.ir/), carrier rules and the gateway's terms before use. Public [Ministry guidance](https://www.ict.gov.ir/fa/newsagency/25160) addresses subscriber permission and unwanted promotional SMS. This tool does not certify legal compliance, check carrier suppression registers or authorize use of a personal SIM for campaigns.

### Opt-out exclusions

Maintain a private UTF-8 CSV with header `phone`, one number per row. It is mandatory in live mode; a reviewed empty list contains only the header. Set `SMS_EXCLUSIONS_FILE` to its path. Invalid entries abort preflight. Normalized exclusions override consent and duplicates.

Operators must receive withdrawals through their own accessible channel, update this list promptly and recheck it before each run. The tool also compares the bounded exclusion-file digest **before every outbound submission** and stops subsequent requests if that file changes or becomes unreadable. This is a fail-closed snapshot check, not instantaneous opt-out reception: there is still a race between checking and sending, and no automatic inbound STOP handling. Do not continue a running campaign after learning of a withdrawal; interrupt it and reconcile before proceeding.

### Validation, duplicates and personalization

The entire input is validated and rendered before submission. Live mode rejects any invalid records. Limits: 5 MiB per CSV, 10,000 rows, 100-character names and 480 UTF-16 message units. Only plain `{name}` substitution is supported; attribute access, conversions and format specifications are rejected. Control characters in names are rejected; Persian zero-width non-joiners are allowed.

Numbers are normalized before deduplication. The first valid occurrence supplies the message; **all** occurrences must assert consent. A contradictory duplicate denies eligibility for that number. Dry Run reports invalid rows, duplicates, exclusions and missing consent without sending anything.

## Optional live execution: restricted and explicit

No live test is part of CI or repository maintenance. A first real integration test requires **separate explicit approval** and only a maintainer-controlled number with documented consent. Never test with the bundled example recipients.

1. Review the recipients, evidence, exclusions, rendered template, provider/carrier permissions and costs privately.
2. Configure a private `.env` with credentials, your campaign CSV, non-demo consent scope and exclusion CSV.
3. Set `SMS_DRY_RUN=false`, `SMS_SEND_ENABLED=true`, a conservative positive `SMS_ESTIMATED_UNIT_COST` **per SMS segment**, and positive `SMS_MAX_ESTIMATED_COST` in the same currency.
4. Run `python main.py` to preview the aggregate preflight. Without `--live`, even live-configured environments remain simulations.
5. Only after review, supply `--live --campaign-id <stable-id> --confirm-campaign <same-id>`. Both environment switches and matching CLI confirmation are required. If Dry Run is true, `--live` is refused.

A live run prints its current preflight before making requests. Do not use a new ID to bypass an uncertain or rejected campaign. IDs must contain 1–64 ASCII letters, digits, hyphens or underscores.

### Operational bounds and estimates

| Setting | Default / boundary |
|---|---|
| `SMS_MAX_RECIPIENTS` | 100 eligible unique recipients; allowed 1–1000 |
| `SMS_DELAY_BETWEEN_SMS` | 2 seconds; allowed 1–3600, sequential requests only |
| `SMS_REQUEST_TIMEOUT` | 10 seconds; allowed 1–60 |
| `SMS_ESTIMATED_UNIT_COST` | 0; positive conservative per-segment estimate required live |
| `SMS_MAX_ESTIMATED_COST` | 0; positive estimate cap required live |
| `SMS_MANIFEST_DIR` | `campaign-state` |

Costs use a conservative Unicode segmentation assumption: 70 UTF-16 units for a single segment, 67 per multipart segment, even for Latin messages. Supplementary characters count as two units. Actual provider/carrier segmentation, encoding, tariffs, taxes and charges may differ. The cap bounds this **estimate**, not a verified financial guarantee; configure provider-side spending restrictions too.

A campaign whose `recipients × (delay + timeout)` estimate exceeds one hour is refused. This is not a hard wall-clock deadline: Requests timeouts are socket inactivity bounds. No parallelism, automatic retries, rate-limit bypass, scheduling or unattended sending is implemented.

## Safe reruns and local journal

`manifest.py` writes a private JSON journal **before** each HTTP request, under an exclusive campaign lock. It stores status and salted opaque number references, not names, full numbers or message bodies. Files are created with restrictive permissions where supported; use a private directory on a local filesystem. References remain pseudonymous personal data, not anonymized information.

Reuse the same ID and directory for the same campaign. Accepted recipients are skipped. A pending/unknown or rejected prior result blocks remaining submissions until the operator reconciles it with the provider; there is no automatic override or resend. An interruption between completed requests can resume only untouched recipients. A changed eligible recipient/message plan, endpoint or consent scope refuses reuse of the ID. Updating exclusions can change that plan: stop and reconcile rather than bypassing the refusal with a fresh ID.

A stale `.lock` intentionally blocks execution. Remove it only after independently confirming no process is running and reconciling pending outcomes. Do not delete/edit journals to force a rerun. Losing the journal, changing IDs/directories, using separate hosts or copying state cannot provide global duplicate protection. Exactly-once delivery is **not** promised.

## Gateway contract and outcomes

Verified against the official [sending guide](https://docs.sms-gate.app/features/sending-messages/), [API specification](https://capcom6.github.io/android-sms-gateway/) and [authentication guide](https://docs.sms-gate.app/integration/authentication/).

- Default: `POST https://api.sms-gate.app/3rdparty/v1/messages`, Basic authentication, `textMessage.text`, one E.164 `phoneNumbers` entry and `ttl=3600`. The old `message` field is deprecated; the old singular route is not assumed supported.
- Override with `SMS_SERVER_ADDRESS` or `SMS_API_ENDPOINT` for a trusted compatible deployment. Live endpoints must use HTTPS, without URL credentials, query parameters or fragments. Plain HTTP local gateways require a trusted TLS proxy; redirects are not followed. Local mode uses the device directly; cloud mode queues via the server. Both require operator verification of the deployed API version.
- Documented enqueue response is HTTP 202. Compatible 200/201 responses are accepted only with a nonempty string `id` and a recognized positive state (`Pending`, `Processed`, `Sent`, `Delivered`). `Failed`/`Cancelled` mean rejected. Unexpected schemas/states are unknown. Provider identifiers and response bodies are never logged or retained.
- 400/404/405/413/422: invalid request; 401/403: authentication; 429: throttling. These stop the run. Other HTTP errors, 5xx/queue unavailability, malformed acknowledgements and transport errors are conservatively unknown and stop the run. No blind retry is attempted.

A gateway may accept a message before a timeout or a local disk failure. The journal then preserves a pending/unknown claim. This is not proof of rejection or delivery. There is no receipt polling or carrier delivery-rate calculation. Gateway-side queues and carrier restrictions must still be respected.

## Results and exit codes

Counters separate input records, valid rows, eligible unique recipients, duplicate rows, exclusions, missing consent, prior journal outcomes, simulations, accepted/rejected/unknown attempts and unattempted recipients after a stop. Duplicate rows are counted separately; exclusion and consent counters refer to unique valid numbers. Validation failures are **not** gateway attempts.

API acceptance percentage = current-run accepted ÷ (accepted + rejected + unknown), or 0 with no attempts. It excludes previews, validation failures and previous runs.

| Exit | Meaning |
|---|---|
| 0 | Successful preview or permitted submissions; deliberate exclusions are reported, not errors |
| 2 | Invalid configuration/input or authorization; no live submission starts after failed preflight |
| 3 | Accepted and rejected results, including retained journal results |
| 4 | Rejected results with no accepted results |
| 5 | Unknown result, interruption, changed/unreadable opt-out file or operational failure; reconcile before rerunning |

Unknown outcomes take precedence. Failure diagnostics are fixed, redacted classifications; stdout contains JSON events without recipient data. Argparse usage errors also use exit 2.

## Privacy and security

Routine diagnostics contain aggregate counts and fixed classifications only: no names, numbers, message bodies, credentials, endpoint URLs or provider bodies. Logging is console-only; old `SMS_LOG_FILE`/`SMS_LOG_LEVEL` settings no longer enable file/debug output. Protect any shell-captured output yourself.

Keep `.env`, lists, evidence and journals private. Default local state, contact files and reports are ignored by Git and Docker. Custom state directories must also be kept outside the build context. Retain journals while retries/reconciliation remain possible; archive securely under your retention policy, and delete them only after the campaign is permanently retired. Deleting state removes rerun protection. Retain the minimum authorized suppression data needed to honor withdrawals; removing it carelessly can permit recontact. Deletion from backups and secure storage are operator responsibilities.

See [SECURITY.md](SECURITY.md). No privacy-law or production-delivery certification is claimed.

## Tests, CI and Docker

```bash
python -m unittest discover -s tests -v
python -m pip install coverage ruff pip-audit
coverage run --source=main,campaign,config,manifest,sms_service,utils -m unittest discover -s tests
coverage report --show-missing --fail-under=80
ruff check --select E9,F63,F7,F82 .
python -m pip_audit -r requirements.txt
```

CI checks Python 3.10–3.14, static correctness, measured coverage including `main.py`, dependencies, tracked dataset hygiene and a non-root Python 3.14 Docker Dry Run with networking disabled. Unit tests use synthetic recipients and mocked HTTP; no gateway credentials are supplied.

```bash
docker build -t batch-sms-campaign-automation .
docker run --rm --network none \
  -e SMS_CSV_FILE_PATH=/tmp/contacts.csv \
  -v "$PWD/examples/contacts.example.csv:/tmp/contacts.csv:ro" \
  batch-sms-campaign-automation
```

No environment file or credentials are needed for this demonstration. Live containers require separately authorized execution and durable private state/data mounts with appropriate non-root permissions; an ephemeral container alone cannot preserve rerun protection.

## Structure and limits

`main.py` composes strict `config.py`, bounded `campaign.py`, the local `manifest.py` journal and `sms_service/sms_sender.py`; `utils/` contains normalization and logging. No CRM, database, queue framework, scheduling, inbound opt-out responder or multi-provider broker is added. Public source and examples are MIT licensed.
