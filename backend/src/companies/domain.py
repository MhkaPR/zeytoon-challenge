"""Domain-value helpers for the companies module."""

from urllib.parse import urlsplit


def normalize_domain(raw):
    """Return a normalized company domain for storage.

    Lowercases and strips any scheme/path/query while preserving the hostname, including
    a leading ``www.``, because the hostname is also used as the crawl seed. Duplicate
    detection uses :func:`canonical_domain` separately.
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
    return value.strip(".")


def canonical_domain(raw):
    """Return the duplicate-detection key, treating www and apex as equivalent."""
    value = normalize_domain(raw)
    return value[4:] if value.startswith("www.") else value
