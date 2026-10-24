"""SMSGate request contract and redacted, conservative submission outcomes."""

import logging
import math
from dataclasses import dataclass
from string import Formatter
import unicodedata

import requests

from utils.phone_formatter import normalize_iranian_mobile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Submission:
    status: str  # accepted, rejected, unknown
    reason: str
    stop: bool = False


class SMSGatewayClient:
    def __init__(
        self,
        endpoint,
        username,
        password,
        message_template,
        timeout_seconds=10,
        *,
        live_authorized=False,
    ):
        self.live_authorized = live_authorized
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.message_template = message_template
        self.timeout_seconds = timeout_seconds
        if not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 60:
            raise ValueError("Request timeout must be between 1 and 60 seconds")
        try:
            for _, field, spec, conversion in Formatter().parse(message_template):
                if field is not None and (field != "name" or spec or conversion):
                    raise ValueError("Only plain {name} placeholders are supported")
            self.render_message("Sample User")
        except (ValueError, KeyError, IndexError):
            raise ValueError(
                "Invalid message template; use only plain {name} placeholders"
            ) from None
        self.session = requests.Session()
        # Do not inherit proxy credentials or .netrc authentication unexpectedly.
        self.session.trust_env = False

    def validate_recipient(self, phone_number):
        return normalize_iranian_mobile(phone_number)

    def render_message(self, recipient_name):
        if len(recipient_name) > 100 or any(
            unicodedata.category(c).startswith("C") and c != "\u200c"
            for c in recipient_name
        ):
            raise ValueError("Invalid recipient name")
        message = self.message_template.format(name=recipient_name.strip())
        if not message.strip() or len(message.encode("utf-16-be")) // 2 > 480:
            raise ValueError("Message must contain 1 to 480 UTF-16 code units")
        return message

    def submit_message(self, phone_number, message):
        """No retries or redirect following. Acceptance is not carrier delivery."""
        if not self.live_authorized:
            raise ValueError("Gateway submission requires explicit live authorization")
        normalized = self.validate_recipient(phone_number)
        try:
            response = self.session.post(
                self.endpoint,
                json={
                    "textMessage": {"text": message},
                    "phoneNumbers": [normalized],
                    "ttl": 3600,
                },
                headers={"Content-Type": "application/json"},
                auth=(self.username, self.password),
                timeout=self.timeout_seconds,
                allow_redirects=False,
            )
        except requests.RequestException:
            result = Submission("unknown", "transport_error", True)
        else:
            result = self._classify(response)
        logger.info("Gateway outcome: %s (%s)", result.status, result.reason)
        return result

    @staticmethod
    def _classify(response):
        code = response.status_code
        if code in {401, 403}:
            return Submission("rejected", "authentication", True)
        if code == 429:
            return Submission("rejected", "rate_limited", True)
        if code in {400, 404, 405, 413, 422}:
            return Submission("rejected", "invalid_request", True)
        if code not in {200, 201, 202}:
            return Submission(
                "unknown", "unavailable" if code >= 500 else "unexpected_http", True
            )
        try:
            data = response.json()
        except ValueError:
            return Submission("unknown", "malformed_response", True)
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("id"), str)
            or not data["id"].strip()
        ):
            return Submission("unknown", "malformed_response", True)
        state = data.get("state")
        if not isinstance(state, str):
            return Submission("unknown", "malformed_response", True)
        if state in {"Pending", "Processed", "Sent", "Delivered"}:
            return Submission("accepted", "acknowledged")
        if state in {"Failed", "Cancelled"}:
            return Submission("rejected", "provider_rejected", True)
        return Submission("unknown", "unknown_state", True)
