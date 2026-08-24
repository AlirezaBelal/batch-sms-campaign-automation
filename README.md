# Batch Messaging Delivery System

A compact Python workflow for processing contact data, generating personalized messages, and submitting them to an external SMS gateway with rate control and structured logging.

This repository is a **sanitized portfolio snapshot** of a personal automation workflow used for a campaign of approximately **5,000 contacts**. It focuses on the implementation and operational safeguards rather than campaign content or recipient data.

> **Delivery semantics:** an API response such as `Pending` means the provider accepted/queued the request. It is **not** a carrier delivery receipt and should not be interpreted as final delivery confirmation.

## What it demonstrates

- Batch CSV processing
- Personalized message templating
- Iranian mobile-number normalization
- External REST API integration with Basic Auth
- Configurable rate limiting between requests
- Timeout and request-error handling
- Privacy-safe logging with masked phone numbers
- Environment-based secret management
- Explicit opt-in before outbound sending
- Containerized execution with Docker
- Small unit-test coverage for normalization/privacy helpers

## Processing flow

```text
CSV contacts
    ↓
Schema validation
    ↓
Phone normalization
    ↓
Message rendering
    ↓
Rate-controlled API submission
    ↓
Provider acknowledgement / failure
    ↓
Masked structured logs
```

## Project structure

```text
.
├── main.py                     # Batch orchestration and runtime safeguards
├── config.py                   # Environment-based configuration
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── sms_service/
│   └── sms_sender.py           # Provider API client and message rendering
├── utils/
│   ├── logger.py               # File + console logging
│   └── phone_formatter.py      # Iranian mobile normalization and masking
└── tests/
    └── test_phone_formatter.py # Normalization and masking tests
```

## Requirements

- Python 3.8+
- Access to a compatible SMS gateway
- A CSV file containing recipient names and phone numbers

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Configuration is loaded from environment variables. For local development, create a `.env` file in the repository root. `.env` files are ignored by Git.

```dotenv
SMS_SERVER_ADDRESS=https://your-sms-provider.example
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

`SMS_SEND_ENABLED` defaults to `false`. The application will not submit outbound messages until it is explicitly set to `true`.

### Important configuration rules

- Never commit live credentials.
- Keep recipient CSV files outside version control.
- Review the message template and input file before enabling sending.
- Rotate any credential that has ever been exposed publicly or committed to Git history.

## Input format

The default CSV schema expects:

```csv
first_name_per,selected_phone
Ali,09121234567
Sara,+989121234567
```

Column names can be changed with `SMS_FIRST_NAME_COLUMN` and `SMS_PHONE_COLUMN`.

The current phone formatter is intentionally scoped to **Iranian mobile numbers** and normalizes supported inputs to `+98...` format.

## Run locally

```bash
python main.py
```

If credentials are missing or `SMS_SEND_ENABLED` is not enabled, the program exits before making outbound requests.

## Run with Docker

Build the image:

```bash
docker build -t batch-messaging-delivery-system .
```

Run with your local environment and data mounted at runtime:

```bash
docker run --rm \
  --env-file .env \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/logs:/app/logs" \
  batch-messaging-delivery-system
```

Recipient data and credentials are intentionally not copied into the image.

## Tests

The repository uses Python's built-in `unittest`, so there is no additional test dependency:

```bash
python -m unittest discover -s tests -v
```

The current tests cover common Iranian mobile-number formats, invalid input rejection, and phone-number masking used in logs.

## Logging and privacy

The workflow logs processing outcomes to both the console and a log file. Phone numbers are masked before being written to logs so that routine execution output does not expose full recipient numbers.

Generated logs, local `.env` files, CSV data, and local databases are excluded through `.gitignore` and `.dockerignore`.

## Status semantics

The application counts HTTP-accepted requests as **API accepted/queued**. This metric describes submission to the gateway only.

It does **not** claim:

- carrier delivery confirmation
- recipient receipt/read status
- a final SMS delivery rate

A provider state of `Pending` is logged as queued rather than delivered.

## Current scope and limitations

- Single-process sequential batch execution
- Configurable delay between submissions, but no distributed rate limiter
- No delivery-receipt polling in this repository
- No automatic retry queue for failed requests
- CSV input only in this public snapshot
- Iranian mobile-number normalization is intentionally country-specific

These constraints are explicit so the repository reflects what the code actually implements rather than overstating production capabilities.

## Portfolio context

This repository focuses on code and implementation details. For broader project context and other product/data work, see the **[portfolio](https://alirezabelal.github.io/)**.
