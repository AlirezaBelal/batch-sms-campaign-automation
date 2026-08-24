"""SMS gateway client used by the campaign application."""

import logging
from typing import Tuple

import requests

from utils.phone_formatter import mask_phone_number, normalize_iranian_mobile

logger = logging.getLogger(__name__)


class SMSGatewayClient:
    """Validate recipients, render messages and submit requests to an SMS gateway."""

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        message_template: str,
        timeout_seconds: int = 10,
    ) -> None:
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.message_template = message_template
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def validate_recipient(self, phone_number: str) -> str:
        """Normalize and validate one Iranian mobile number."""
        return normalize_iranian_mobile(phone_number)

    def submit_message(self, phone_number: str, message: str) -> Tuple[bool, object]:
        """Submit one message and report whether the provider accepted the request.

        A successful API response is an acknowledgement only. A provider state
        such as ``Pending`` is not a carrier delivery receipt.
        """
        masked_phone = mask_phone_number(phone_number)

        try:
            normalized_phone = self.validate_recipient(phone_number)
            masked_phone = mask_phone_number(normalized_phone)

            response = self.session.post(
                self.endpoint,
                json={"message": message, "phoneNumbers": [normalized_phone]},
                headers={"Content-Type": "application/json"},
                auth=(self.username, self.password),
                timeout=self.timeout_seconds,
            )

            if response.status_code in {200, 201, 202}:
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {"raw_response": response.text[:500]}

                provider_state = response_data.get("state")
                message_id = response_data.get("id")

                if provider_state == "Pending":
                    logger.info(
                        "Gateway accepted/queued request for %s%s",
                        masked_phone,
                        f" (id={message_id})" if message_id else "",
                    )
                else:
                    logger.info(
                        "Gateway accepted request for %s (state=%s)",
                        masked_phone,
                        provider_state or "unknown",
                    )

                return True, response_data

            logger.error(
                "Gateway rejected request for %s with HTTP %s",
                masked_phone,
                response.status_code,
            )
            return False, response.text[:500]

        except ValueError as exc:
            logger.warning("Skipping invalid mobile number %s: %s", masked_phone, exc)
            return False, str(exc)
        except requests.exceptions.Timeout:
            logger.error("Gateway request timed out for %s", masked_phone)
            return False, "Request timed out"
        except requests.exceptions.ConnectionError:
            logger.error("Gateway connection failed for %s", masked_phone)
            return False, "Connection error"
        except requests.RequestException as exc:
            logger.error("Gateway request failed for %s: %s", masked_phone, exc)
            return False, str(exc)

    def render_message(self, recipient_name: str) -> str:
        """Render the configured message template for one recipient."""
        return self.message_template.format(name=(recipient_name or "").strip())
