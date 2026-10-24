"""Strict environment configuration; absent execution flags always mean Dry Run."""

import math
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    dry_run: bool = True
    send_enabled: bool = False
    endpoint: str = "https://api.sms-gate.app/3rdparty/v1/messages"
    username: str = ""
    password: str = ""
    input_file: str = "examples/contacts.example.csv"
    name_column: str = "first_name_per"
    phone_column: str = "selected_phone"
    template: str = "Hello {name}, this is a sample message."
    timeout: float = 10
    delay: float = 2
    max_recipients: int = 100
    unit_cost: Decimal = Decimal("0")
    max_cost: Decimal = Decimal("0")
    consent_scope: str = "demo"
    exclusions_file: str = ""
    manifest_dir: str = "campaign-state"

    def validate(self, live: bool = False) -> None:
        if not (math.isfinite(self.delay) and 1 <= self.delay <= 3600):
            raise ValueError("SMS_DELAY_BETWEEN_SMS must be between 1 and 3600 seconds")
        if not (math.isfinite(self.timeout) and 1 <= self.timeout <= 60):
            raise ValueError("SMS_REQUEST_TIMEOUT must be between 1 and 60 seconds")
        if not 1 <= self.max_recipients <= 1000:
            raise ValueError("SMS_MAX_RECIPIENTS must be between 1 and 1000")
        if any(not x.is_finite() or x < 0 for x in (self.unit_cost, self.max_cost)):
            raise ValueError("Cost estimates must be finite and nonnegative")
        if (
            not self.name_column
            or not self.phone_column
            or self.name_column == self.phone_column
        ):
            raise ValueError("CSV name and phone columns must be distinct and nonempty")
        if live:
            if self.dry_run or not self.send_enabled:
                raise ValueError(
                    "Live execution requires SMS_DRY_RUN=false and SMS_SEND_ENABLED=true"
                )
            if self.consent_scope == "demo" or not all(
                (self.username, self.password, self.consent_scope, self.exclusions_file)
            ):
                raise ValueError(
                    "Live execution requires credentials, consent scope and an exclusion CSV"
                )
            url = urlsplit(self.endpoint)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError(
                    "Gateway endpoint must be HTTPS without credentials, query or fragment"
                )
            if self.unit_cost <= 0 or self.max_cost <= 0:
                raise ValueError(
                    "Live execution requires positive unit-cost and total-cost estimates"
                )


def _boolean(env, name, default):
    value = env.get(name, default).strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return value == "true"


def load_settings(env=None):
    if env is None:
        load_dotenv()
        env = os.environ
    try:
        settings = Settings(
            dry_run=_boolean(env, "SMS_DRY_RUN", "true"),
            send_enabled=_boolean(env, "SMS_SEND_ENABLED", "false"),
            endpoint=env.get(
                "SMS_API_ENDPOINT",
                env.get("SMS_SERVER_ADDRESS", "https://api.sms-gate.app").rstrip("/")
                + "/3rdparty/v1/messages",
            ),
            username=env.get("SMS_USERNAME", ""),
            password=env.get("SMS_PASSWORD", ""),
            input_file=env.get("SMS_CSV_FILE_PATH", "examples/contacts.example.csv"),
            name_column=env.get("SMS_FIRST_NAME_COLUMN", "first_name_per"),
            phone_column=env.get("SMS_PHONE_COLUMN", "selected_phone"),
            template=env.get("SMS_MESSAGE_TEMPLATE", Settings.template),
            timeout=float(env.get("SMS_REQUEST_TIMEOUT", "10")),
            delay=float(env.get("SMS_DELAY_BETWEEN_SMS", "2")),
            max_recipients=int(env.get("SMS_MAX_RECIPIENTS", "100")),
            unit_cost=Decimal(env.get("SMS_ESTIMATED_UNIT_COST", "0")),
            max_cost=Decimal(env.get("SMS_MAX_ESTIMATED_COST", "0")),
            consent_scope=env.get("SMS_CONSENT_SCOPE", "demo"),
            exclusions_file=env.get("SMS_EXCLUSIONS_FILE", ""),
            manifest_dir=env.get("SMS_MANIFEST_DIR", "campaign-state"),
        )
        settings.validate()
        return settings
    except (ValueError, InvalidOperation):
        raise ValueError(
            "Invalid campaign configuration; check documented types and bounds"
        ) from None
