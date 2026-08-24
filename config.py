"""Configuration for the batch messaging application.

Secrets and environment-specific values are loaded from environment variables.
Never commit live credentials to this file.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# SMS service configuration
SERVER_ADDRESS = os.getenv("SMS_SERVER_ADDRESS", "https://api.sms-gate.app").rstrip("/")
USERNAME = os.getenv("SMS_USERNAME", "")
PASSWORD = os.getenv("SMS_PASSWORD", "")
API_ENDPOINT = os.getenv(
    "SMS_API_ENDPOINT",
    f"{SERVER_ADDRESS}/3rdparty/v1/message",
)

# Sending is opt-in to reduce accidental sends while testing/configuring.
SEND_ENABLED = os.getenv("SMS_SEND_ENABLED", "false").lower() in {"1", "true", "yes"}

# CSV configuration
CSV_FILE_PATH = os.getenv("SMS_CSV_FILE_PATH", "data/contacts.csv")
FIRST_NAME_COLUMN = os.getenv("SMS_FIRST_NAME_COLUMN", "first_name_per")
PHONE_COLUMN = os.getenv("SMS_PHONE_COLUMN", "selected_phone")

# Message template. Keep the public default generic; customize locally as needed.
MESSAGE_TEMPLATE = os.getenv(
    "SMS_MESSAGE_TEMPLATE",
    "Hello {name}, this is a sample message.",
)

# Logging configuration
LOG_LEVEL = os.getenv("SMS_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("SMS_LOG_FILE", "logs/sms_sender.log")

# Request configuration
REQUEST_TIMEOUT = int(os.getenv("SMS_REQUEST_TIMEOUT", "10"))
DELAY_BETWEEN_SMS = float(os.getenv("SMS_DELAY_BETWEEN_SMS", "2"))
