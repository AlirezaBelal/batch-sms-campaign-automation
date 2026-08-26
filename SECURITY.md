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

This repository is a portfolio snapshot of a campaign-submission workflow, not a managed messaging service. Operators are responsible for securing deployment credentials, campaign data, and the host environment.

The provided `.env.example` starts in Dry Run mode and disables live sending. Real credentials and recipient datasets must remain outside source control. Any credential that is accidentally exposed in a public repository or log should be revoked or rotated immediately.
