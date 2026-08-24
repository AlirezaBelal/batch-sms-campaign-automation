"""Application entry point for the batch messaging workflow."""
import csv
import os
import time

from config import (
    SERVER_ADDRESS,
    USERNAME,
    PASSWORD,
    API_ENDPOINT,
    SEND_ENABLED,
    CSV_FILE_PATH,
    FIRST_NAME_COLUMN,
    PHONE_COLUMN,
    MESSAGE_TEMPLATE,
    DELAY_BETWEEN_SMS,
    REQUEST_TIMEOUT,
)
from sms_service.sms_sender import SMSSender
from utils.logger import setup_logger

logger = setup_logger()


def read_csv_and_submit_messages(csv_file_path, sms_sender):
    """Read contacts from CSV and submit messages to the provider API.

    Returns:
        tuple[int, int]: ``(accepted_or_queued, failed)`` counts.
    """
    accepted = 0
    failed = 0

    if not os.path.exists(csv_file_path):
        logger.error("CSV file not found: %s", csv_file_path)
        return accepted, failed

    try:
        with open(csv_file_path, "r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file)
            header = next(reader, None)

            if not header:
                logger.error("CSV file is empty: %s", csv_file_path)
                return accepted, failed

            try:
                first_name_index = header.index(FIRST_NAME_COLUMN)
                phone_index = header.index(PHONE_COLUMN)
            except ValueError as exc:
                logger.error("Required CSV column not found: %s", exc)
                return accepted, failed

            for row_num, row in enumerate(reader, start=2):
                try:
                    if len(row) <= max(first_name_index, phone_index):
                        logger.warning("Row %s has insufficient columns; skipping", row_num)
                        failed += 1
                        continue

                    name = row[first_name_index].strip()
                    phone = row[phone_index].strip()

                    if not phone:
                        logger.warning("Row %s has an empty phone number; skipping", row_num)
                        failed += 1
                        continue

                    message = sms_sender.create_message(name)
                    accepted_by_api, _ = sms_sender.send_sms(phone, message)

                    if accepted_by_api:
                        accepted += 1
                    else:
                        failed += 1

                    if DELAY_BETWEEN_SMS > 0:
                        time.sleep(DELAY_BETWEEN_SMS)

                except Exception as exc:
                    logger.error("Error processing row %s: %s", row_num, exc)
                    failed += 1

    except OSError as exc:
        logger.error("Error reading CSV file: %s", exc)

    return accepted, failed


def validate_runtime_config():
    """Check required runtime configuration before any outbound request."""
    missing = []
    if not USERNAME:
        missing.append("SMS_USERNAME")
    if not PASSWORD:
        missing.append("SMS_PASSWORD")

    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        return False

    if not SEND_ENABLED:
        logger.warning(
            "Sending is disabled. Set SMS_SEND_ENABLED=true only after reviewing "
            "credentials, input data and message content."
        )
        return False

    return True


def main():
    logger.info("Starting batch messaging process")

    if not validate_runtime_config():
        return

    sms_sender = SMSSender(
        SERVER_ADDRESS,
        USERNAME,
        PASSWORD,
        API_ENDPOINT,
        MESSAGE_TEMPLATE,
        timeout=REQUEST_TIMEOUT,
    )

    accepted, failed = read_csv_and_submit_messages(CSV_FILE_PATH, sms_sender)
    total = accepted + failed

    logger.info(
        "Process completed. Total processed: %s, API accepted/queued: %s, Failed: %s",
        total,
        accepted,
        failed,
    )

    if total > 0:
        acceptance_rate = (accepted / total) * 100
        logger.info(
            "API acceptance/queue rate: %.2f%% (not a carrier delivery rate)",
            acceptance_rate,
        )


if __name__ == "__main__":
    main()
