"""Structured JSON logging with masking of sensitive identifiers.

The masking rules are mandatory (spec FR-026): logs MUST NOT contain full phone numbers,
one-time codes, or tokens.
"""

import json
import logging
import re

# Mask any run of 7+ digits that looks like a phone number, keeping a short prefix/suffix.
_PHONE_RE = re.compile(r"(\+?\d{2,4})\d{3,}(\d{3,4})")
# Redact bearer tokens / long opaque strings.
_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b")
# Redact explicit key: value pairs for codes/tokens/phone numbers.
_KV_RE = re.compile(
    r"(?i)\b(code|otp|token|access_token|refresh_token|phone|phone_number)"
    r"(\s*[=:]\s*)([^\s,;\"'}]+)"
)


def _national_format(value):
    """Render a phone number in its national format, or ``None`` when it cannot be parsed."""
    try:
        from django.conf import settings
        from phonenumbers import PhoneNumberFormat, format_number, parse

        parsed = parse(str(value).strip(), settings.PHONE_DEFAULT_REGION)
        return format_number(parsed, PhoneNumberFormat.NATIONAL)
    except Exception:
        return None


def mask_phone(value):
    """Mask a phone number in a form its owner still recognizes (e.g. ``0912***6789``).

    The national-format rendering keeps the number recognizable in the UI (the user sees
    their own number) while never exposing the full value (spec FR-026). Numbers that cannot
    be parsed fall back to a plain digit mask.
    """
    digits = re.sub(r"\D", "", _national_format(value) or str(value))
    if len(digits) <= 4:
        return "*" * len(digits)
    if len(digits) <= 8:
        return f"{digits[:2]}{'*' * (len(digits) - 4)}{digits[-2:]}"
    return f"{digits[:4]}***{digits[-4:]}"


def mask_text(text):
    """Apply all masking rules to a free-form string."""
    if not isinstance(text, str):
        text = str(text)
    text = _TOKEN_RE.sub("[redacted-token]", text)
    text = _PHONE_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)
    text = _KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]", text)
    return text


class SensitiveDataFilter(logging.Filter):
    """Logging filter that masks sensitive identifiers in messages and arguments."""

    def filter(self, record):
        record.msg = mask_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: mask_text(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(
                    mask_text(value) if isinstance(value, str) else value
                    for value in record.args
                )
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record):
        payload = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("event", "phone", "provider", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)
