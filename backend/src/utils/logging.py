"""Structured JSON logging with redaction of sensitive secrets.

One-time codes and tokens are never written to logs in full. Phone numbers are treated as
ordinary identifiers and are logged as-is when an event explicitly includes them.
"""

import json
import logging
import re

# Redact bearer tokens / long opaque strings.
_TOKEN_RE = re.compile(
    r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"
)
# Redact explicit key: value pairs for codes/tokens.
_KV_RE = re.compile(
    r"(?i)\b(code|otp|token|access_token|refresh_token)"
    r"(\s*[=:]\s*)([^\s,;\"'}]+)"
)


def mask_text(text):
    """Apply the redaction rules to a free-form string."""
    if not isinstance(text, str):
        text = str(text)
    text = _TOKEN_RE.sub("[redacted-token]", text)
    text = _KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]", text)
    return text


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts secrets in messages and arguments."""

    def filter(self, record):
        # Render the message before redacting so placeholders and their arguments stay in
        # sync; leaving the original args behind would make a later ``getMessage()`` fail.
        record.msg = mask_text(record.getMessage())
        record.args = None
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
