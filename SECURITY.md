# Security Policy

## Supported version

Security fixes are applied to the latest revision of the `master` branch. Older snapshots are not maintained as separate supported releases.

## Reporting a vulnerability

Do not publish credentials, recipient data, exploit details, or other sensitive information in a public issue.

If GitHub private vulnerability reporting is available for this repository, use the repository's **Security** tab. Otherwise, open a minimal public issue that contains no sensitive details and asks for a private reporting channel.

Useful reports include a clear description of the affected component, the security impact, reproducible steps that do not expose real recipient data, and a suggested mitigation when available.

## Security-sensitive areas

Please report issues involving:

- exposure of gateway credentials or environment-backed secrets
- unintended live message submission or bypass of Dry Run / send controls
- recipient phone numbers or names leaking into logs or source control
- unsafe handling of campaign CSV files or generated logs
- request authentication, transport, or endpoint configuration problems
- vulnerable runtime dependencies or container configuration

## Operational safety

This repository provides an operator-controlled campaign-submission CLI, not a managed or compliance-certified messaging service. Operators are responsible for securing deployment credentials, campaign data, and the host environment.

The provided `.env.example` starts in Dry Run mode and disables live sending. Real credentials and recipient datasets must remain outside source control. Any credential that is accidentally exposed in a public repository or log should be revoked or rotated immediately.

## Consent and operational boundaries

Missing consent metadata, an exclusion match, incomplete live authorization or
failed preflight must prevent submission. Consent metadata is an operator assertion,
not independent legal evidence. Do not use purchased, scraped or unverified lists.
Operators must verify current jurisdiction, carrier and provider requirements and
maintain an authorized opt-out list; this application does not process inbound SMS.
A changed or unreadable suppression file is detected before each HTTP submission
by comparing a bounded file digest with the preflight snapshot, then the run stops.
This is not an atomic provider opt-out check; withdrawals must be ingested promptly
by the operator and a small check-to-send race remains. Never treat the unchanged
file as evidence of current consent. Embedded phone field control characters and
oversized values are rejected, not normalized into a plausible number.

Treat the local journal as sensitive pseudonymous data. Keep it on a private local
filesystem with restrictive permissions and backups protected under a retention
policy. Never remove state or choose a new campaign ID to retry uncertain outcomes.
Reconcile provider status first. No exactly-once or carrier-delivery guarantee exists.

All maintenance tests must remain offline with synthetic fixtures and mocked HTTP.
A real test requires separate explicit approval and a maintainer-controlled number.
