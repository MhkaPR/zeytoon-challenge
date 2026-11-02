"""Phone-number validation and normalization using the ``phonenumbers`` library."""

from django.conf import settings
from phonenumbers import NumberParseException, format_number, is_valid_number, parse
from phonenumbers import PhoneNumberFormat


def normalize_phone(raw_number):
    """Return the number in E.164 form, or ``None`` when it is not valid.

    Validity follows the configured default region (spec FR-018): invalid input is rejected
    before any code is created or SMS is sent.
    """
    if raw_number is None:
        return None
    raw = str(raw_number).strip()
    if not raw:
        return None
    try:
        parsed = parse(raw, settings.PHONE_DEFAULT_REGION)
    except NumberParseException:
        return None
    if not is_valid_number(parsed):
        return None
    return format_number(parsed, PhoneNumberFormat.E164)
