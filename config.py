"""
Configuration settings for the SMS sending application
"""
# SMS Service Configuration
SERVER_ADDRESS = "https://api.sms-gate.app"
USERNAME = "YGRC8Z"
PASSWORD = "toi6yk2ucadvmy"
API_ENDPOINT = f"{SERVER_ADDRESS}/3rdparty/v1/message"

# CSV Configuration
CSV_FILE_PATH = "data/test.csv"
FIRST_NAME_COLUMN = "first_name_per"
PHONE_COLUMN = "selected_phone"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_FILE = "logs/sms_sender.log"

# Request Configuration
REQUEST_TIMEOUT = 10  # seconds
DELAY_BETWEEN_SMS = 2  # seconds
