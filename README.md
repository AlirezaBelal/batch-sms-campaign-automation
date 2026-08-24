# Batch SMS Campaign Automation

[![CI](https://github.com/AlirezaBelal/batch-sms-campaign-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/AlirezaBelal/batch-sms-campaign-automation/actions/workflows/ci.yml)

> A product-oriented Python workflow for controlled, personalized batch SMS campaigns with safe simulation, input validation, request pacing, gateway submission, and privacy-aware logging.

This project addresses a practical operational problem:

**How can a personalized SMS campaign be executed for thousands of contacts without preparing messages one by one, while keeping the workflow controlled, observable, repeatable, and safe to operate?**

The original workflow was used for a campaign involving approximately **5,000 contacts**. This repository is a sanitized portfolio snapshot: recipient data, live credentials, and campaign-specific content are intentionally excluded.

## Product context

At campaign scale, the operating problem is larger than simply calling an SMS API:

- contact data can be inconsistent
- phone numbers can use different representations
- messages need per-recipient personalization
- outbound requests need pacing
- one bad record should not terminate the campaign
- credentials and contact data must remain outside source control
- operators need a clear execution summary
- gateway acknowledgement must not be confused with final carrier delivery

The product goal is to reduce repetitive campaign operations while preserving:

**control · repeatability · observability · data hygiene**

## What the application does

```text
Contact CSV
    ↓
Schema validation
    ↓
Campaign orchestration
    ↓
Recipient extraction
    ↓
Message rendering
    ↓
Iranian mobile validation / normalization
    ↓
┌──────────────────────────┬──────────────────────────┐
│ Dry Run                  │ Live Run                 │
│ validate + simulate      │ rate-controlled submit   │
│ no gateway request       │ external SMS gateway     │
└──────────────────────────┴──────────────────────────┘
    ↓
CampaignResult + privacy-aware logs
```

## Core capabilities

- **Campaign orchestration** through a dedicated `CampaignRunner`
- **CSV batch processing** with row-level failure isolation
- **Personalized message rendering** through a configurable template
- **Iranian mobile normalization** into a consistent `+98...` representation
- **Safe Dry Run mode** that validates the full campaign without network submission
- **Authenticated REST gateway integration** for live runs
- **Configurable request pacing** between live submissions
- **Masked phone-number logging**
- **Environment-backed configuration and secret handling**
- **Dockerized execution**
- **Automated tests and GitHub Actions CI**

## Delivery semantics

This repository implements a **campaign submission workflow**, not a complete messaging platform.

A successful gateway response means the provider accepted or queued the request.

> A state such as `Pending` is a provider queue acknowledgement. It is **not** a carrier delivery receipt and does not prove that the recipient received the SMS.

Live campaign metrics therefore describe:

- contacts processed
- API accepted / queued requests
- failed submissions
- API acceptance / queue rate

Dry Run metrics are kept separate and report:

- simulated records
- validation failures

The application does **not** claim carrier-confirmed delivery, recipient receipt/read status, or a final SMS delivery rate.

## Architecture

```text
                 ┌────────────────────┐
                 │    Contact CSV     │
                 └─────────┬──────────┘
                           ▼
                 ┌────────────────────┐
                 │   CampaignRunner   │
                 │    campaign.py     │
                 └─────────┬──────────┘
                           ▼
             ┌──────────────────────────┐
             │     SMSGatewayClient     │
             │ render + validate + REST │
             └─────────────┬────────────┘
                           │
                Dry Run? ──┤
                    │      │
                  yes      no
                    │      │
                    ▼      ▼
              simulation  gateway API
                    │      │
                    └──┬───┘
                       ▼
               ┌──────────────┐
               │CampaignResult│
               └──────────────┘
```

`main.py` is the composition root: it configures logging, validates runtime safety settings, wires the gateway client to the campaign runner, and reports the final result.

## Repository structure

```text
.
├── main.py
├── campaign.py
├── config.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── examples/
│   └── contacts.example.csv
├── sms_service/
│   ├── __init__.py
│   └── sms_sender.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── phone_formatter.py
├── tests/
│   ├── test_campaign.py
│   └── test_phone_formatter.py
└── .github/workflows/
    └── ci.yml
```

## Requirements

- Python 3.8+
- an SMS gateway only for live sending
- a CSV file containing recipient names and Iranian mobile numbers

## Quick start: safe Dry Run

### 1. Clone and install

```bash
git clone https://github.com/AlirezaBelal/batch-sms-campaign-automation.git
cd batch-sms-campaign-automation
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Create local configuration

Linux / macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The example configuration starts safely with:

```dotenv
SMS_DRY_RUN=true
SMS_SEND_ENABLED=false
SMS_CSV_FILE_PATH=examples/contacts.example.csv
```

No SMS credentials are required for Dry Run.

### 3. Run the simulation

```bash
python main.py
```

Dry Run executes CSV parsing, schema validation, message rendering, mobile-number normalization, error handling, aggregation, and logging — but sends **no HTTP request** to the SMS gateway.

Expected summary shape:

```text
Dry run completed. Total processed: 2, Simulated: 2, Failed validation: 0
```

The bundled `examples/contacts.example.csv` contains synthetic-looking test data intended only for Dry Run and format demonstration. **Do not use the bundled example recipients for live sending.**

## SMS Gateway for Android setup

The default gateway configuration in this repository is compatible with **SMS Gateway for Android**. For live sending, install and configure the Android application using the provider's official installation guide:

**[SMS Gateway for Android — Installation Guide](https://docs.sms-gate.app/installation/)**

Use the official installation page rather than a version-specific APK link so the setup instructions continue to point to the provider's current release.

After installing the Android gateway, configure the credentials and endpoint issued by your selected gateway mode in your local `.env` file. Provider credentials belong only in local/environment configuration and must never be committed to the repository.

The application keeps the gateway endpoint configurable through `SMS_SERVER_ADDRESS` and `SMS_API_ENDPOINT`, so the campaign layer is not tied to a hard-coded deployment URL.

## Live campaign execution

Use live mode only after reviewing the campaign and configuring valid provider credentials.

```dotenv
SMS_DRY_RUN=false
SMS_SEND_ENABLED=true

SMS_USERNAME=your_username
SMS_PASSWORD=your_password
SMS_SERVER_ADDRESS=https://your-provider.example

SMS_CSV_FILE_PATH=data/contacts.csv
SMS_MESSAGE_TEMPLATE=Hello {name}, this is a sample message.
SMS_DELAY_BETWEEN_SMS=2
```

Then run:

```bash
python main.py
```

For a first integration test, use a CSV containing only a mobile number you control.

## Input format

Default columns:

```csv
first_name_per,selected_phone
Example User,09XXXXXXXXX
```

Column names are configurable using `SMS_FIRST_NAME_COLUMN` and `SMS_PHONE_COLUMN`.

Real recipient datasets should never be committed to the repository.

## Configuration reference

| Environment variable | Purpose | Default |
|---|---|---|
| `SMS_DRY_RUN` | Run full validation/simulation with no gateway request | `false` in code; `true` in `.env.example` |
| `SMS_SEND_ENABLED` | Explicit live-send safety switch | `false` |
| `SMS_SERVER_ADDRESS` | Provider base URL | provider-specific default in code |
| `SMS_API_ENDPOINT` | Override provider message endpoint | derived from base URL |
| `SMS_USERNAME` | Gateway username | required for live mode |
| `SMS_PASSWORD` | Gateway password | required for live mode |
| `SMS_CSV_FILE_PATH` | Campaign CSV path | `data/contacts.csv` |
| `SMS_FIRST_NAME_COLUMN` | Recipient-name column | `first_name_per` |
| `SMS_PHONE_COLUMN` | Recipient-phone column | `selected_phone` |
| `SMS_MESSAGE_TEMPLATE` | Message template with `{name}` support | generic sample |
| `SMS_REQUEST_TIMEOUT` | Gateway request timeout | `10` seconds |
| `SMS_DELAY_BETWEEN_SMS` | Delay between live submissions | `2` seconds |
| `SMS_LOG_LEVEL` | Logging level | `INFO` |
| `SMS_LOG_FILE` | Log output path | `logs/sms_campaign.log` |

### Safety precedence

If both values are accidentally enabled:

```dotenv
SMS_DRY_RUN=true
SMS_SEND_ENABLED=true
```

**Dry Run takes precedence and no gateway request is sent.**

## Tests

Run locally:

```bash
python -m unittest discover -s tests -v
```

Current tests cover:

- Iranian mobile-number normalization
- invalid/non-mobile rejection
- privacy-safe phone masking
- campaign row processing
- API acceptance aggregation
- missing-phone handling
- Dry Run simulation without gateway submission
- Dry Run validation failures

## Continuous Integration

GitHub Actions runs automatically on pushes and pull requests to `master`.

CI verifies:

- dependency installation
- Python compilation / syntax
- dependency consistency
- unit tests across supported Python versions
- Docker image buildability

The CI badge at the top of this README reflects the latest workflow state.

## Docker

Build:

```bash
docker build -t batch-sms-campaign-automation .
```

Run safely using the example Dry Run configuration:

```bash
docker run --rm \
  --env-file .env \
  -v "$PWD/examples:/app/examples:ro" \
  -v "$PWD/logs:/app/logs" \
  batch-sms-campaign-automation
```

For live operation, mount your private campaign data rather than baking it into the image.

## Operational safeguards

**Credentials** — secrets are loaded from environment variables and `.env` is excluded from version control.

**Recipient privacy** — contact datasets and generated logs are excluded from source control; routine logs mask phone numbers.

**Safe simulation** — Dry Run validates the campaign without network submission and does not require provider credentials.

**Explicit live opt-in** — live sending requires both `SMS_DRY_RUN=false` and `SMS_SEND_ENABLED=true`.

**Failure isolation** — one malformed record does not terminate the remaining campaign.

**Credential rotation** — any credential that has ever been exposed publicly or committed to Git history must be revoked or rotated; deleting it from the current branch is not sufficient.

## Current scope and limitations

The public snapshot intentionally remains a focused campaign automation application:

- sequential single-process execution
- CSV input
- configurable request delay rather than a distributed rate limiter
- no automatic retry queue/backoff workflow
- no resumable campaign checkpointing
- no scheduling layer
- no opt-out management
- no multi-provider routing
- no delivery-receipt polling
- no campaign dashboard
- no final delivery analytics

These are potential product extensions, not capabilities claimed by the current implementation.

## Why this project matters

The value is not simply calling an SMS API. The repository demonstrates how a repetitive operational task can be translated into a small productized application with explicit safety and product boundaries:

**structured input → validation → personalization → safe simulation → controlled execution → observability → explicit delivery semantics**

## Portfolio

For broader project context and other product/data work, see **[alirezabelal.github.io](https://alirezabelal.github.io/)**.
