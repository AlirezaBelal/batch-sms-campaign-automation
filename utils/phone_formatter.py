"""Phone-number normalization and privacy helpers."""


def convert_to_international_format(phone_number):
    """Normalize an Iranian mobile number to E.164-like ``+98...`` format.

    Accepted examples include ``0912...``, ``912...``, ``98912...`` and
    ``0098912...``. Invalid or non-mobile values raise ``ValueError``.
    """
    digits = "".join(filter(str.isdigit, str(phone_number)))

    if digits.startswith("0098"):
        digits = digits[2:]

    if digits.startswith("98"):
        national_number = digits[2:]
    elif digits.startswith("0"):
        national_number = digits[1:]
    else:
        national_number = digits

    if len(national_number) != 10 or not national_number.startswith("9"):
        raise ValueError("Invalid Iranian mobile number")

    return f"+98{national_number}"


def mask_phone_number(phone_number):
    """Return a privacy-safe representation for logs."""
    digits = "".join(filter(str.isdigit, str(phone_number)))
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"
