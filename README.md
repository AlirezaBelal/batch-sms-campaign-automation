# Batch SMS Campaign Automation

> A product-oriented Python workflow for running controlled, personalized batch SMS campaigns through an external gateway.

This project was built around a practical operational problem:

**How can a personalized SMS campaign be executed for thousands of contacts without preparing messages one by one, while keeping the workflow controlled, observable, repeatable, and safe to operate?**

The application reads structured contact data, validates campaign input, normalizes Iranian mobile numbers, renders personalized messages, submits them to an SMS gateway with configurable pacing, and records submission outcomes in privacy-aware logs.

The original workflow was used for a campaign involving approximately **5,000 contacts**. This repository is a sanitized portfolio snapshot: recipient data, live credentials, and campaign-specific content are intentionally excluded.

## Product context

A small number of personalized messages can be handled manually. At campaign scale, the operating problem changes:

- contact data may be inconsistent
- phone numbers may use different representations
- messages need per-recipient personalization
- outbound requests need pacing
- one bad row should not terminate the batch
- credentials and contact data must stay outside source control
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
Mobile-number normalization
    ↓
Message rendering
    ↓
Rate-controlled gateway submission
    ↓
Accepted / queued / failed result
    ↓
Privacy-aware logs + campaign summary
```

### Core capabilities

**Campaign orchestration**  
Separates campaign execution from the command-line entry point through a dedicated `CampaignRunner`.

**Batch processing**  
Processes recipient records from a structured CSV file while isolating row-level failures.

**Personalization**  
Renders a configurable message template for each recipient.

**Iranian mobile normalization**  
Normalizes supported local and international representations into a consistent `+98...` format and rejects malformed/non-mobile values.

**Gateway integration**  
Uses an authenticated REST client dedicated to SMS-provider submission.

**Request pacing**  
Adds a configurable delay between submissions to avoid uncontrolled request bursts.

**Operational logging**  
Records campaign outcomes while masking phone numbers in routine logs.

**Safe-by-default sending**  
Outbound submission remains disabled until `SMS_SEND_ENABLED=true` is explicitly configured.

## Product boundaries

This repository implements a **campaign submission workflow**, not a complete messaging platform.

A successful API response means the configured provider accepted or queued the request.

> A state such as `Pending` is a provider queue acknowledgement. It is **not** a carrier delivery receipt and does not prove that the recipient received the SMS.

The application therefore reports:

- contacts processed
- API accepted / queued requests
- failed submissions
- API acceptance / queue rate

It does **not** claim:

- carrier-confirmed delivery
- recipient receipt or read status
- final SMS delivery rate

## Architecture

```text
                 ┌────────────────────┐
                 │    Contact CSV     │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │   CampaignRunner   │
                 │    campaign.py     │
                 └─────────┬──────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   ┌──────────────────┐        ┌──────────────────┐
   │ Mobile Normalizer│        │ Message Renderer │
   └─────────┬────────┘        └─────────┬────────┘
             └─────────────┬─────────────┘
                           ▼
                 ┌────────────────────┐
                 │  SMSGatewayClient  │
                 │   REST submission  │
                 └─────────┬──────────┘
                           ▼
                 ┌────────────────────┐
                 │ External SMS       │
                 │ Gateway            │
                 └─────────┬──────────┘
                           ▼
                 ┌────────────────────┐
                 │ Masked logs +      │
                 │ CampaignResult     │
                 └────────────────────┘
```

`main.py` acts as the composition root: it configures logging, validates safety-critical settings, wires the gateway client to the campaign runner, executes one campaign run, and prints the aggregate result.

## Repository structure

```text
.
├── main.py                       # Application entry point / component wiring
├── campaign.py                   # Campaign orchestration and result model
├── config.py                     # Environment-backed runtime configuration
├── .env.example                  # Safe configuration template
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── sms_service/
│   └── sms_sender.py             # SMSGatewayClient / provider integration
├── utils/
│   ├── logger.py                 # Central logging configuration
│   └── phone_formatter.py        # Iranian mobile normalization + masking
└── tests/
    ├── test_campaign.py          # Campaign orchestration tests
    └── test_phone_formatter.py   # Normalization and privacy-helper tests
```

## Requirements

- Python 3.8+
- access to a compatible SMS gateway
- a CSV file containing recipient names and mobile numbers

## Run locally

### 1. Clone

```bash
git clone https://github.com/AlirezaBelal/batch-sms-campaign-automation.git
cd batch-sms-campaign-automation
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create local configuration

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually or with PowerShell.

Then configure your gateway credentials and campaign settings in `.env`.

```dotenv
SMS_SERVER_ADDRESS=https://your-provider.example
SMS_USERNAME=your_username
SMS_PASSWORD=your_password
SMS_SEND_ENABLED=false

SMS_CSV_FILE_PATH=data/contacts.csv
SMS_FIRST_NAME_COLUMN=first_name_per
SMS_PHONE_COLUMN=selected_phone

SMS_MESSAGE_TEMPLATE=Hello {name}, this is a sample message.
SMS_REQUEST_TIMEOUT=10
SMS_DELAY_BETWEEN_SMS=2
```

The `.env` file is ignored by Git.

### 5. Prepare campaign input

The default input path is:

```text
data/contacts.csv
```

Default schema:

```csv
first_name_per,selected_phone
Ali,09121234567
Sara,+989121234567
```

Column names can be changed using `SMS_FIRST_NAME_COLUMN` and `SMS_PHONE_COLUMN`.

> Real recipient datasets should not be committed to the repository.

### 6. Review the safety gate

Sending is disabled by default:

```dotenv
SMS_SEND_ENABLED=false
```

Before enabling outbound requests, review:

- provider credentials
- campaign input
- recipient list
- message template
- request delay

Only then set:

```dotenv
SMS_SEND_ENABLED=true
```

### 7. Run

```bash
python main.py
```

If credentials are missing or outbound sending has not explicitly been enabled, the application exits before submitting any request.

## Configuration reference

| Environment variable | Purpose | Default |
|---|---|---|
| `SMS_SERVER_ADDRESS` | SMS provider base URL | provider-specific default in code |
| `SMS_API_ENDPOINT` | Override message endpoint | derived from base URL |
| `SMS_USERNAME` | Gateway username | required |
| `SMS_PASSWORD` | Gateway password | required |
| `SMS_SEND_ENABLED` | Explicit outbound-send safety switch | `false` |
| `SMS_CSV_FILE_PATH` | Campaign CSV path | `data/contacts.csv` |
| `SMS_FIRST_NAME_COLUMN` | Recipient-name column | `first_name_per` |
| `SMS_PHONE_COLUMN` | Recipient-phone column | `selected_phone` |
| `SMS_MESSAGE_TEMPLATE` | Message template; supports `{name}` | generic sample |
| `SMS_REQUEST_TIMEOUT` | Gateway timeout in seconds | `10` |
| `SMS_DELAY_BETWEEN_SMS` | Delay between submissions | `2` |
| `SMS_LOG_LEVEL` | Logging level | `INFO` |
| `SMS_LOG_FILE` | Log output path | `logs/sms_campaign.log` |

## Docker

Build the image:

```bash
docker build -t batch-sms-campaign-automation .
```

Run with local configuration and data mounted at runtime:

```bash
docker run --rm \
  --env-file .env \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/logs:/app/logs" \
  batch-sms-campaign-automation
```

Credentials and recipient data are supplied at runtime rather than baked into the image.

## Tests

The project uses Python's built-in `unittest` framework:

```bash
python -m unittest discover -s tests -v
```

Current tests cover:

- common Iranian mobile-number representations
- invalid/non-mobile rejection
- phone-number masking for logs
- campaign row processing
- API acceptance aggregation
- missing-phone handling without gateway submission

## Operational safeguards

### Credentials

Secrets are loaded from environment variables. Live credentials should never be committed.

If a credential has ever appeared in public Git history, removing it from the current version is not sufficient; revoke or rotate it at the provider.

### Recipient data

Contact lists may contain personal information. General CSV data, generated logs, local environment files, and local databases are excluded from version control.

### Logging

Routine logs mask recipient phone numbers so application output does not unnecessarily expose full contact data.

### Failure isolation

A malformed or rejected record is counted as failed without terminating the remaining campaign run.

### Delivery semantics

The campaign result models **gateway submission outcomes**, not final telecom delivery. This distinction is intentionally reflected in variable names, logs, documentation, and metrics.

## Current limitations

The public snapshot deliberately keeps the product scope small:

- single-process sequential execution
- CSV input
- configurable request delay rather than a distributed rate limiter
- no retry queue/backoff workflow
- no resumable campaign checkpointing
- no scheduling layer
- no opt-out management
- no multi-provider routing
- no delivery-receipt polling
- no campaign dashboard
- no final delivery analytics

These are possible product extensions, not capabilities claimed by the current implementation.

## Product evolution

A natural evolution from this workflow toward a broader campaign platform would be:

```text
Contact ingestion
      ↓
Audience validation
      ↓
Campaign configuration
      ↓
Template management
      ↓
Scheduling
      ↓
Queue / worker execution
      ↓
Provider delivery receipts
      ↓
Retry & failure management
      ↓
Campaign analytics
```

The current repository intentionally focuses on the smaller, well-defined layer: **controlled batch campaign submission**.

## Why this project matters

The main value is not simply calling an SMS API. It demonstrates how a repetitive operational task can be translated into a small productized application with clear boundaries:

**structured input → validation → personalization → controlled execution → observability → explicit delivery semantics**

That combination of product thinking and hands-on implementation is the purpose of this repository.

## Portfolio

For broader project context and other product/data work, see **[alirezabelal.github.io](https://alirezabelal.github.io/)**.
