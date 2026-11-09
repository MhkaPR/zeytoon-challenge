"""Redis-backed state for one-time codes and lockout counters.

One-time codes and attempt counters are intentionally NOT database models: they live in the
configured cache (Redis in every real environment) with an explicit expiry so they disappear
without a sweeper (see research.md R2/R7). Expiry is stored in the payload rather than read
back through backend-specific TTL APIs, so the code works with any Django cache backend.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from constance import config
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _otp_key(phone_number):
    return f"otp:{_normalize(phone_number)}"


def _lockout_key(phone_number):
    return f"otp:lockout:{_normalize(phone_number)}"


def _failure_key(phone_number):
    return f"otp:failures:{_normalize(phone_number)}"


def _source_key(source):
    return f"otp:source:{source}"


def _normalize(phone_number):
    """Normalize a phone number for use in a cache key (best effort)."""
    from apps.accounts.validation import normalize_phone

    return normalize_phone(phone_number) or str(phone_number)


def hash_code(code):
    """Return an HMAC-SHA256 hash of a one-time code keyed by the server secret."""
    secret = settings.OTP_HASH_SECRET.encode()
    return hmac.new(secret, str(code).encode(), hashlib.sha256).hexdigest()


def generate_code():
    """Generate a random numeric code of the configured length."""
    length = int(config.OTP_LENGTH)
    upper = 10**length
    return str(secrets.randbelow(upper)).zfill(length)


def store_code(phone_number, code, ttl_seconds=None):
    """Store the hashed code with a TTL, replacing any previous code for the phone."""
    ttl = int(ttl_seconds if ttl_seconds is not None else config.OTP_TTL_SECONDS)
    payload = {
        "code_hash": hash_code(code),
        "attempts": 0,
        "expires_at": (timezone.now() + timedelta(seconds=ttl)).isoformat(),
    }
    cache.set(_otp_key(phone_number), payload, timeout=ttl)
    return ttl


def get_code(phone_number):
    """Return the stored code payload, or ``None`` when absent/expired."""
    payload = cache.get(_otp_key(phone_number))
    if payload is None:
        return None
    expires_at = payload.get("expires_at")
    if expires_at and timezone.now().isoformat() > expires_at:
        cache.delete(_otp_key(phone_number))
        return None
    return payload


def increment_attempts(phone_number, payload, ttl_seconds=None):
    """Increment the failed-attempt counter for the active code."""
    payload = dict(payload)
    payload["attempts"] = int(payload.get("attempts", 0)) + 1
    ttl = int(ttl_seconds if ttl_seconds is not None else config.OTP_TTL_SECONDS)
    cache.set(_otp_key(phone_number), payload, timeout=ttl)
    return payload["attempts"]


def delete_code(phone_number):
    cache.delete(_otp_key(phone_number))


def code_ttl(phone_number):
    """Remaining TTL of the active code in seconds, or ``0`` when absent."""
    payload = get_code(phone_number)
    if payload is None:
        return 0
    remaining = timezone.datetime.fromisoformat(payload["expires_at"]) - timezone.now()
    return max(int(remaining.total_seconds()), 0)


def set_lockout(phone_number, seconds=None):
    """Lock the phone number for the configured duration."""
    duration = int(seconds if seconds is not None else config.LOCKOUT_DURATION_SECONDS)
    cache.set(_lockout_key(phone_number), True, timeout=duration)
    return duration


def is_locked_out(phone_number):
    return cache.get(_lockout_key(phone_number)) is True


def clear_lockout(phone_number):
    cache.delete(_lockout_key(phone_number))
    cache.delete(_failure_key(phone_number))


def lockout_ttl(phone_number):
    return (
        0 if not is_locked_out(phone_number) else int(config.LOCKOUT_DURATION_SECONDS)
    )


def bump_failed_attempts(phone_number, ttl_seconds=None):
    """Increment and return the rolling failed-verification count for a phone."""
    window = int(
        ttl_seconds if ttl_seconds is not None else config.LOCKOUT_DURATION_SECONDS
    )
    key = _failure_key(phone_number)
    current = cache.get(key, 0) + 1
    cache.set(key, current, timeout=window)
    return current


def bump_source_counter(source, ttl_seconds=3600):
    """Increment and return the per-source request counter within a window."""
    key = _source_key(source)
    current = cache.get(key, 0) + 1
    cache.set(key, current, timeout=ttl_seconds)
    return current
