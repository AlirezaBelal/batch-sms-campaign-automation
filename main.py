"""Command-line entry point for Batch SMS Campaign Automation."""

import logging

from campaign import CampaignRunner
from config import (
    CAMPAIGN_INPUT_FILE,
    DRY_RUN_ENABLED,
    GATEWAY_MESSAGE_ENDPOINT,
    GATEWAY_PASSWORD,
    GATEWAY_USERNAME,
    MESSAGE_TEMPLATE,
    RECIPIENT_NAME_COLUMN,
    RECIPIENT_PHONE_COLUMN,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SEND_ENABLED,
)
from sms_service import SMSGatewayClient
from utils.logger import configure_logging

logger = logging.getLogger(__name__)


def validate_runtime_config() -> bool:
    """Validate safety-critical configuration before campaign execution."""
    if DRY_RUN_ENABLED:
        if SEND_ENABLED:
            logger.warning(
                "SMS_DRY_RUN=true takes precedence over SMS_SEND_ENABLED=true; "
                "no gateway requests will be sent."
            )
        return True

    missing_variables = []

    if not GATEWAY_USERNAME:
        missing_variables.append("SMS_USERNAME")
    if not GATEWAY_PASSWORD:
        missing_variables.append("SMS_PASSWORD")

    if missing_variables:
        logger.error(
            "Missing required environment variables: %s",
            ", ".join(missing_variables),
        )
        return False

    if not SEND_ENABLED:
        logger.warning(
            "Outbound sending is disabled. Use SMS_DRY_RUN=true for a safe full "
            "campaign simulation, or set SMS_SEND_ENABLED=true only after reviewing "
            "credentials, campaign data, message content and request pacing."
        )
        return False

    return True


def main() -> None:
    """Initialize application components and execute one campaign run."""
    configure_logging()
    logger.info("Starting SMS campaign automation")

    if not validate_runtime_config():
        return

    gateway_client = SMSGatewayClient(
        endpoint=GATEWAY_MESSAGE_ENDPOINT,
        username=GATEWAY_USERNAME,
        password=GATEWAY_PASSWORD,
        message_template=MESSAGE_TEMPLATE,
        timeout_seconds=REQUEST_TIMEOUT_SECONDS,
    )

    campaign = CampaignRunner(
        gateway=gateway_client,
        input_file=CAMPAIGN_INPUT_FILE,
        recipient_name_column=RECIPIENT_NAME_COLUMN,
        recipient_phone_column=RECIPIENT_PHONE_COLUMN,
        request_delay_seconds=REQUEST_DELAY_SECONDS,
        dry_run=DRY_RUN_ENABLED,
    )

    result = campaign.run()

    if DRY_RUN_ENABLED:
        logger.info(
            "Dry run completed. Total processed: %s, Simulated: %s, Failed validation: %s",
            result.total_processed,
            result.simulated,
            result.failed,
        )
        return

    logger.info(
        "Campaign run completed. Total processed: %s, API accepted/queued: %s, Failed: %s",
        result.total_processed,
        result.accepted_or_queued,
        result.failed,
    )

    if result.total_processed:
        logger.info(
            "API acceptance/queue rate: %.2f%% (not a carrier delivery rate)",
            result.api_acceptance_rate,
        )


if __name__ == "__main__":
    main()
