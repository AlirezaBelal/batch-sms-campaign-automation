"""SMS API client for the batch messaging application."""
import requests

from utils.logger import setup_logger
from utils.phone_formatter import convert_to_international_format, mask_phone_number

logger = setup_logger()


class SMSSender:
    def __init__(self, server, username, password, endpoint, message_template, timeout=10):
        """Initialize the SMS sender with provider configuration."""
        self.server = server
        self.username = username
        self.password = password
        self.endpoint = endpoint
        self.message_template = message_template
        self.timeout = timeout

    def send_sms(self, phone_number, message):
        """Submit one message to the provider API.

        A ``True`` result means the provider API accepted the request. It does
        not prove carrier delivery. In particular, a provider state of
        ``Pending`` is a queue acknowledgement, not a delivery receipt.
        """
        masked_phone = mask_phone_number(phone_number)

        try:
            international_phone = convert_to_international_format(phone_number)
            masked_phone = mask_phone_number(international_phone)

            response = requests.post(
                self.endpoint,
                json={
                    "message": message,
                    "phoneNumbers": [international_phone],
                },
                headers={"Content-Type": "application/json"},
                auth=(self.username, self.password),
                timeout=self.timeout,
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
                        "Provider accepted/queued message for %s%s",
                        masked_phone,
                        f" (id={message_id})" if message_id else "",
                    )
                else:
                    logger.info(
                        "Provider accepted message request for %s (state=%s)",
                        masked_phone,
                        provider_state or "unknown",
                    )

                return True, response_data

            logger.error(
                "Provider rejected message for %s with HTTP %s",
                masked_phone,
                response.status_code,
            )
            return False, response.text[:500]

        except ValueError as exc:
            logger.warning("Skipping invalid phone number %s: %s", masked_phone, exc)
            return False, str(exc)
        except requests.exceptions.Timeout:
            logger.error("Request timed out for %s", masked_phone)
            return False, "Request timed out"
        except requests.exceptions.ConnectionError:
            logger.error("Connection error for %s", masked_phone)
            return False, "Connection error"
        except requests.RequestException as exc:
            logger.error("Request error for %s: %s", masked_phone, exc)
            return False, str(exc)

    def create_message(self, name):
        """Render the configured personalized message template."""
        return self.message_template.format(name=(name or "").strip())
