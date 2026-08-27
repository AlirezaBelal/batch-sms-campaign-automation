"""Iranian mobile-number normalization and privacy helpers."""

import re


_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)
_ALLOWED_PHONE_CHARACTERS = re.compile(r"^[0-9+\s().-]+$")


def normalize_iranian_mobile(phone_number: object) -> str:
    """Normalize a supported Iranian mobile number to ``+98...`` format.

    Accepted inputs include national and international representations such as
    ``0912...``, ``912...``, ``98912...`` and ``0098912...``. Persian and
    Arabic digits are converted to ASCII. Visual separators are accepted, but
    embedded text and malformed plus signs raise ``ValueError`` instead of
    being silently removed.
    """
    raw_value = str(phone_number).strip().translate(_DIGIT_TRANSLATION)

    if not raw_value or not _ALLOWED_PHONE_CHARACTERS.fullmatch(raw_value):
        raise ValueError("Invalid Iranian mobile number")

    if raw_value.count("+") > 1 or ("+" in raw_value and not raw_value.startswith("+")):
        raise ValueError("Invalid Iranian mobile number")

    digits = re.sub(r"\D", "", raw_value)

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


def mask_phone_number(phone_number: object) -> str:
    """Return a privacy-safe phone representation for operational logs."""
    normalized_value = str(phone_number).translate(_DIGIT_TRANSLATION)
    digits = "".join(filter(str.isdigit, normalized_value))
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"
