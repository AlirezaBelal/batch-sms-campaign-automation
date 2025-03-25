"""
Phone number formatting utility for the SMS sending application
"""


def convert_to_international_format(phone_number):
    """
    Convert phone number to international format with +98 prefix (Iran)
    
    Args:
        phone_number (str): The phone number to convert
        
    Returns:
        str: The phone number in international format
    """
    # Remove any spaces or special characters
    phone_number = ''.join(filter(str.isdigit, str(phone_number)))

    # Handle different formats
    if phone_number.startswith('0'):
        return "+98" + phone_number[1:]
    elif phone_number.startswith('98'):
        return "+" + phone_number
    elif phone_number.startswith('+98'):
        return phone_number
    else:
        return "+98" + phone_number
