"""
Logging utility for the SMS sending application
"""
import logging
import os


def setup_logger():
    """Set up and return a configured logger"""
    from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Configure logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)
