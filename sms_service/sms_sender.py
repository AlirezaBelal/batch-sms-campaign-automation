"""
SMS sending service for the SMS sending application
"""
import requests

from utils.logger import setup_logger
from utils.phone_formatter import convert_to_international_format

logger = setup_logger()


class SMSSender:
    def __init__(self, server, username, password, endpoint, timeout=10):
        """
        Initialize the SMS sender
        
        Args:
            server (str): Server address
            username (str): Authentication username
            password (str): Authentication password
            endpoint (str): API endpoint
            timeout (int): Request timeout in seconds
        """
        self.server = server
        self.username = username
        self.password = password
        self.endpoint = endpoint
        self.timeout = timeout

    def send_sms(self, phone_number, message):
        """
        Send SMS to a single phone number
        
        Args:
            phone_number (str): Recipient phone number
            message (str): Message text
            
        Returns:
            tuple: (success, response)
        """
        # Convert phone number to international format
        international_phone = convert_to_international_format(phone_number)

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "message": message,
            "phoneNumbers": [international_phone]
        }

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                auth=(self.username, self.password),
                timeout=self.timeout
            )

            if response.status_code in [200, 201, 202]:
                response_json = response.json()
                if response_json.get('state') == 'Pending':
                    logger.info(
                        f"Message queued for sending to {phone_number} ({international_phone}) with ID: {response_json.get('id')}")
                else:
                    logger.info(f"Message successfully sent to {phone_number} ({international_phone})")
                return True, response_json
            else:
                logger.error(
                    f"Error sending message to {phone_number} ({international_phone}): "
                    f"{response.status_code} - {response.text}"
                )
                return False, response.text

        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending message to {phone_number} ({international_phone})")
            return False, "Request timed out"
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error sending message to {phone_number} ({international_phone})")
            return False, "Connection error"
        except Exception as e:
            logger.error(f"Exception sending message to {phone_number} ({international_phone}): {str(e)}")
            return False, str(e)

    def create_message(self, name):
        """
        Create a personalized message for the recipient
        
        Args:
            name (str): Recipient name
            
        Returns:
            str: Personalized message
        """
        return f"""{name} عزیز
سال نوت مبارک! امیدوارم سفره هفت‌سینت پر برکت و زندگیت سرشار از شادی و سلامتی باشه. 
دلت شاد، جیبت پر پول و خونه‌ت پر از عشق و محبت.
به امید دیدنت در سال جدید!
علیرضا بلال"""
