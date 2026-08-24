"""Runtime configuration for Batch SMS Campaign Automation.

Environment variables are the public configuration interface. Internal names
use product/domain terminology so application code remains easy to read.
"""

import os

from dotenv import load_dotenv

load_dotenv()

_TRUE_VALUES = {"1", "true", "yes", "on"}

# Provider gateway
GATEWAY_BASE_URL = os.getenv("SMS_SERVER_ADDRESS", "https://api.sms-gate.app").rstrip("/")
GATEWAY_USERNAME = os.getenv("SMS_USERNAME", "")
GATEWAY_PASSWORD = os.getenv("SMS_PASSWORD", "")
GATEWAY_MESSAGE_ENDPOINT = os.getenv(
    "SMS_API_ENDPOINT",
    f"{GATEWAY_BASE_URL}/3rdparty/v1/message",
)

# Campaign safety and input
DRY_RUN_ENABLED = os.getenv("SMS_DRY_RUN", "false").strip().lower() in _TRUE_VALUES
SEND_ENABLED = os.getenv("SMS_SEND_ENABLED", "false").strip().lower() in _TRUE_VALUES
CAMPAIGN_INPUT_FILE = os.getenv("SMS_CSV_FILE_PATH", "data/contacts.csv")
RECIPIENT_NAME_COLUMN = os.getenv("SMS_FIRST_NAME_COLUMN", "first_name_per")
RECIPIENT_PHONE_COLUMN = os.getenv("SMS_PHONE_COLUMN", "selected_phone")

# Message content
MESSAGE_TEMPLATE = os.getenv(
    "SMS_MESSAGE_TEMPLATE",
    "Hello {name}, this is a sample message.",
)

# Operational logging
LOG_LEVEL = os.getenv("SMS_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
LOG_FILE = os.getenv("SMS_LOG_FILE", "logs/sms_campaign.log")

# Gateway request behavior
REQUEST_TIMEOUT_SECONDS = int(os.getenv("SMS_REQUEST_TIMEOUT", "10"))
REQUEST_DELAY_SECONDS = float(os.getenv("SMS_DELAY_BETWEEN_SMS", "2"))
