"""
Main application entry point for the SMS sending application
"""
import csv
import os
import time

from config import (
    SERVER_ADDRESS, USERNAME, PASSWORD, API_ENDPOINT,
    CSV_FILE_PATH, FIRST_NAME_COLUMN, PHONE_COLUMN,
    DELAY_BETWEEN_SMS, REQUEST_TIMEOUT
)
from sms_service.sms_sender import SMSSender
from utils.logger import setup_logger

logger = setup_logger()


def read_csv_and_send_sms(csv_file_path, sms_sender):
    """
    Read CSV file and send SMS to phone numbers
    
    Args:
        csv_file_path (str): Path to CSV file
        sms_sender (SMSSender): SMS sender instance
        
    Returns:
        tuple: (successful_count, failed_count)
    """
    successful = 0
    failed = 0

    try:
        # Make sure the CSV file exists
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file not found: {csv_file_path}")
            return successful, failed

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)

            # Validate required columns
            try:
                first_name_index = header.index(FIRST_NAME_COLUMN)
                phone_index = header.index(PHONE_COLUMN)
            except ValueError as e:
                logger.error(f"Required column not found: {str(e)}")
                return successful, failed

            # Process each row
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                try:
                    if len(row) <= max(first_name_index, phone_index):
                        logger.warning(f"Row {row_num} has insufficient columns. Skipping.")
                        failed += 1
                        continue

                    name = row[first_name_index]
                    phone = row[phone_index]

                    # Skip if phone number is empty
                    if not phone:
                        logger.warning(f"Row {row_num} has empty phone number. Skipping.")
                        failed += 1
                        continue

                    # Create personalized message
                    message = sms_sender.create_message(name)

                    # Send SMS
                    success, response = sms_sender.send_sms(phone, message)

                    if success:
                        successful += 1
                    else:
                        failed += 1

                    # Delay between sending SMS to avoid rate limiting
                    time.sleep(DELAY_BETWEEN_SMS)

                except Exception as e:
                    logger.error(f"Error processing row {row_num}: {str(e)}")
                    failed += 1

    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")

    return successful, failed


def main():
    """Main function"""
    logger.info("Starting SMS sending process")

    # Create SMS sender
    sms_sender = SMSSender(
        SERVER_ADDRESS,
        USERNAME,
        PASSWORD,
        API_ENDPOINT,
        timeout=REQUEST_TIMEOUT
    )

    # Send SMS
    successful, failed = read_csv_and_send_sms(CSV_FILE_PATH, sms_sender)

    # Log results
    total = successful + failed
    logger.info(f"Process completed. Total: {total}, Successful: {successful}, Failed: {failed}")

    # Calculate success rate
    if total > 0:
        success_rate = (successful / total) * 100
        logger.info(f"Success rate: {success_rate:.2f}%")


if __name__ == "__main__":
    main()
