# Batch Messaging Delivery System

> A lightweight batch-messaging workflow designed to turn a contact list into a controlled, personalized outbound messaging operation.

This project was built around a practical operational problem:

**How can a personalized campaign be sent to thousands of contacts without manually preparing messages one by one, while keeping execution controlled, observable, and reasonably safe?**

The workflow processes structured contact data, normalizes phone numbers, renders personalized messages, submits them to an external messaging gateway, and records the result of each submission.

The original workflow was used in a campaign involving approximately **5,000 contacts**. This public repository is a sanitized implementation snapshot: recipient data, credentials, and campaign-specific content are intentionally excluded.

---

## Product context

Sending a few personalized messages manually is simple.

Sending thousands introduces different problems:

- contact data may be inconsistent
- phone numbers may use different formats
- messages need personalization
- gateway requests need pacing
- individual failures should not stop the whole batch
- credentials and recipient data must stay outside source control
- operators need visibility into what was accepted or rejected
- an API acknowledgement must not be confused with final carrier delivery

This project packages those concerns into one repeatable workflow.

### Product goal

Reduce the operational effort of a large personalized messaging campaign while maintaining:

**control · repeatability · observability · data hygiene**

---

## What the system does

```text
Contact CSV
    ↓
Validate input structure
    ↓
Read recipient + phone number
    ↓
Normalize phone number
    ↓
Render personalized message
    ↓
Submit to messaging API
    ↓
Apply request pacing
    ↓
Record accepted / queued / failed result
    ↓
Write privacy-aware logs
```

### Core capabilities

**Batch processing**  
Processes contacts sequentially from a structured CSV file.

**Personalization**  
Renders a configurable message template for each recipient.

**Phone normalization**  
Normalizes supported Iranian mobile-number formats before submission.

**Gateway integration**  
Submits messages through a REST API with authenticated requests.

**Rate control**  
Adds a configurable delay between requests to reduce uncontrolled bursts.

**Failure isolation**  
A malformed row or failed request does not terminate the entire campaign.

**Operational logging**  
Records processing outcomes while masking phone numbers in routine logs.

**Safe-by-default sending**  
Outbound submission is disabled unless it is explicitly enabled through configuration.

---

## Product boundaries

This repository implements the **submission workflow**, not a complete messaging platform.

A successful API response means that the provider has accepted or queued the request.

> `Pending` means **queued by the provider** — it does not prove that the message reached the recipient.

Therefore metrics produced by this project describe:

- processed contacts
- API accepted / queued requests
- failed submissions

They should **not** be interpreted as:

- carrier-confirmed delivery
- recipient receipt
- read status
- final campaign delivery rate

---

## Architecture

```text
                   ┌─────────────────┐
                   │   Contact CSV   │
                   └────────┬────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Batch Orchestrator│
                  │     main.py       │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌─────────────────┐       ┌─────────────────┐
     │ Phone Formatter │       │ Message Renderer│
     └────────┬────────┘       └────────┬────────┘
              └────────────┬────────────┘
                           ▼
                  ┌──────────────────┐
                  │   SMS Sender     │
                  │  REST API Client │
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │ External Gateway │
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │ Masked Logs +    │
                  │ Batch Summary    │
                  └──────────────────┘
```

---

## Repository structure

```text
.
├── main.py
├── config.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── sms_service/
│   └── sms_sender.py
├── utils/
│   ├── logger.py
│   └── phone_formatter.py
└── tests/
    └── test_phone_formatter.py
```

| Component | Responsibility |
|---|---|
| `main.py` | Batch orchestration, CSV validation and execution safeguards |
| `config.py` | Environment-based runtime configuration |
| `sms_service/sms_sender.py` | Message rendering and gateway communication |
| `utils/phone_formatter.py` | Iranian mobile normalization and log masking |
| `utils/logger.py` | Console and file logging |
| `tests/` | Tests for normalization and privacy helpers |

---

# Running the project

## 1. Clone

```bash
git clone https://github.com/AlirezaBelal/batch-messaging-delivery-system.git
cd batch-messaging-delivery-system
```

## 2. Create a virtual environment

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

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Prepare your contact file

By default, the application expects:

```text
data/contacts.csv
```

Example:

```csv
first_name_per,selected_phone
Ali,09121234567
Sara,+989121234567
```

The default required columns are:

```text
first_name_per
selected_phone
```

Both names can be changed through environment variables.

> Real contact datasets should never be committed to the repository.

---

## 5. Configure the environment

Create a local `.env` file:

```dotenv
SMS_SERVER_ADDRESS=https://your-provider.example

SMS_USERNAME=your_username
SMS_PASSWORD=your_password

SMS_CSV_FILE_PATH=data/contacts.csv

SMS_FIRST_NAME_COLUMN=first_name_per
SMS_PHONE_COLUMN=selected_phone

SMS_MESSAGE_TEMPLATE=Hello {name}, this is a sample message.

SMS_REQUEST_TIMEOUT=10
SMS_DELAY_BETWEEN_SMS=2

SMS_SEND_ENABLED=false
```

The `.env` file is ignored by Git.

### Safety switch

The most important setting is:

```dotenv
SMS_SEND_ENABLED=false
```

Sending is disabled by default.

Only after verifying:

- credentials
- input CSV
- recipient list
- message content
- request delay

change it to:

```dotenv
SMS_SEND_ENABLED=true
```

---

## 6. Run

```bash
python main.py
```

If required credentials are missing or sending has not explicitly been enabled, the application exits without submitting messages.

---

## Example execution

```text
Starting batch messaging process

Processing contacts...

Message queued for ********4567
Message accepted for ********2233
Request failed for ********7788

Process completed.
Total processed: 500
API accepted/queued: 487
Failed: 13

API acceptance/queue rate: 97.40%
```

The percentage above is an **API acceptance rate**, not a carrier delivery rate.

---

# Docker

Build:

```bash
docker build -t batch-messaging-delivery-system .
```

Run:

```bash
docker run --rm \
  --env-file .env \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/logs:/app/logs" \
  batch-messaging-delivery-system
```

Recipient files and credentials are supplied at runtime and are not baked into the image.

---

# Tests

Run the current unit tests with:

```bash
python -m unittest discover -s tests -v
```

Current tests focus on:

- Iranian mobile-number normalization
- invalid input handling
- privacy-safe phone masking

---

# Operational safeguards

### Credentials

Secrets are loaded through environment variables rather than committed configuration.

If a credential has ever appeared in public Git history, deleting it from the latest version is **not enough**. It should be revoked or rotated at the provider.

### Recipient data

Contact lists may contain personal information.

The repository therefore excludes local CSV datasets and generated logs from version control.

### Logging

Phone numbers are masked in routine log output to reduce unnecessary exposure of recipient data.

### Accidental sending

Outbound messaging requires an explicit:

```dotenv
SMS_SEND_ENABLED=true
```

This is intentional.

---

# Current limitations

The project deliberately keeps its scope small.

**Current implementation:**

- sequential single-process execution
- CSV-based input
- configurable delay between submissions
- authenticated REST API integration
- provider acknowledgement tracking
- masked logging

**Not currently implemented:**

- carrier delivery-receipt polling
- retry queues with backoff
- resumable campaigns
- distributed workers
- campaign dashboard
- scheduling
- recipient opt-out management
- multi-provider routing
- final delivery analytics

These are product-extension opportunities rather than capabilities claimed by the current repository.

---

# Product evolution

If this workflow were developed into a broader messaging product, the natural next layer would be:

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

That would move the system from a **batch automation workflow** toward a full **campaign delivery platform**.

---

# Why this project matters

The interesting part of this project is not simply calling an SMS API.

It demonstrates how a repetitive operational task can be translated into a small productized workflow with:

**structured input → validation → personalization → controlled execution → observability → explicit operational boundaries**

That combination of product thinking and implementation is the main purpose of this repository.

---

## Portfolio

For the broader project context and other product/data work:

**[alirezabelal.github.io](https://alirezabelal.github.io/)**
