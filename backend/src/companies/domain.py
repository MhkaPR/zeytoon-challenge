"""Domain-value helpers for the companies module."""

import re
from urllib.parse import urlsplit

_WWW_RE = re.compile(r"^www\.", re.IGNORECASE)


def normalize_domain(raw):
    """Return a normalized company domain for storage.

    Lowercases, strips any scheme/path/query, and drops a leading ``www.`` so that the admin
    panel has a consistent key for duplicate detection (FR-041). This module performs **no**
    duplicate detection itself (FR-042).
    """
    if raw is None:
        return ""
    value = str(raw).strip().lower()
    if not value:
        return ""
    if "://" in value:
        value = urlsplit(value).netloc or value.split("://", 1)[1]
    # Drop any path/query/port remnants.
    value = value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    value = value.split(":", 1)[0]
    value = _WWW_RE.sub("", value)
    return value.strip(".")
