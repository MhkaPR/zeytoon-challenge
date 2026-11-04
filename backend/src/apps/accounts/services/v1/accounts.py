"""Domain services for the SMS OTP login flow."""

import hmac
import logging
from urllib.parse import urlsplit

from constance import config
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import state
from apps.accounts.exceptions import ApiError
from apps.accounts.sms import get_gateway
from apps.accounts.validation import normalize_phone

logger = logging.getLogger(__name__)

User = get_user_model()

INCORRECT_CODE_MESSAGE = "The code is incorrect"
BLOCKED_MESSAGE = (
    "To resolve the block, contact us through the following communication channels"
)


# ---------------------------------------------------------------------------
# OTP request
# ---------------------------------------------------------------------------


def request_otp(raw_phone, source=None):
    """Validate the phone, enforce limits, create and dispatch a one-time code."""
    phone = normalize_phone(raw_phone)
    if phone is None:
        raise ApiError("invalid_phone", "The phone number is not valid.")

    if state.is_locked_out(phone):
        raise ApiError(
            "locked_out",
            "Too many attempts. Please try again later.",
            http_status=429,
            fields={"retry_after_seconds": max(state.lockout_ttl(phone) or 0, 0)},
        )

    existing = User.objects.filter(phone_number=phone).first()
    if existing and existing.is_blocked:
        raise ApiError(
            "user_blocked",
            BLOCKED_MESSAGE,
            http_status=409,
            fields={"channels": list(config.CONTACT_CHANNELS)},
        )

    code = state.generate_code()
    ttl = state.store_code(phone, code)
    get_gateway().send_code(phone, code)

    logger.info(
        "otp.requested",
        extra={"event": "otp_requested", "phone": phone},
    )
    return {"status": "sent", "expires_in_seconds": ttl}


# ---------------------------------------------------------------------------
# OTP verification
# ---------------------------------------------------------------------------


def verify_otp(raw_phone, code, return_url=None):
    """Verify the code and log the user in, creating the account implicitly if needed."""
    phone = normalize_phone(raw_phone)
    if phone is None:
        raise ApiError("invalid_phone", "The phone number is not valid.")

    if state.is_locked_out(phone):
        raise ApiError(
            "locked_out",
            "Too many attempts. Please try again later.",
            http_status=429,
            fields={"retry_after_seconds": max(state.lockout_ttl(phone) or 0, 0)},
        )

    existing = User.objects.filter(phone_number=phone).first()
    if existing and existing.is_blocked:
        raise ApiError(
            "user_blocked",
            BLOCKED_MESSAGE,
            http_status=409,
            fields={"channels": list(config.CONTACT_CHANNELS)},
        )

    payload = state.get_code(phone)
    # An absent/expired code is indistinguishable from a wrong one (spec FR-015).
    if payload is None:
        _register_failed_attempt(phone)
        raise ApiError("otp_incorrect", INCORRECT_CODE_MESSAGE)

    if not hmac.compare_digest(payload.get("code_hash", ""), state.hash_code(code)):
        attempts = state.increment_attempts(phone, payload)
        if attempts >= int(config.MAX_VERIFY_ATTEMPTS):
            state.delete_code(phone)
            _register_failed_attempt(phone, force=True)
        else:
            _register_failed_attempt(phone)
        raise ApiError("otp_incorrect", INCORRECT_CODE_MESSAGE)

    # Success: consume the code and clear counters.
    state.delete_code(phone)
    state.clear_lockout(phone)

    with transaction.atomic():
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={"username": phone},
        )

    tokens = issue_tokens(user)
    redirect_to = resolve_return_url(return_url)

    logger.info(
        "otp.verified",
        extra={
            "event": "otp_verified",
            "phone": phone,
        },
    )
    return {
        "user": user,
        "created": created,
        "tokens": tokens,
        "redirect_to": redirect_to,
    }


def _register_failed_attempt(phone, force=False):
    """Track failures and trigger a temporary lockout past the threshold."""
    failures = state.bump_failed_attempts(phone)
    if force or failures >= int(config.LOCKOUT_THRESHOLD):
        state.set_lockout(phone)
        logger.warning(
            "otp.lockout",
            extra={"event": "otp_lockout", "phone": phone},
        )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def issue_tokens(user):
    """Issue an access/refresh token pair for the user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "expires_in": int(refresh.access_token.lifetime.total_seconds()),
    }


def revoke_tokens(refresh_token):
    """Blacklist a refresh token (and thus revoke the session)."""
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import RefreshToken as RT

    try:
        RT(refresh_token).blacklist()
    except TokenError:
        return False
    return True


# ---------------------------------------------------------------------------
# Return URL
# ---------------------------------------------------------------------------


def resolve_return_url(return_url):
    """Return a safe relative path, falling back to the configured default."""
    default = config.DEFAULT_RETURN_PATH
    if not return_url:
        return default

    target = str(return_url).strip()
    # Reject absolute URLs and protocol-relative targets (open-redirect protection).
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return default
    path = parts.path or "/"
    if not path.startswith("/"):
        return default

    allowlist = list(config.RETURN_URL_ALLOWLIST)
    for allowed in allowlist:
        if allowed == "/":
            if path == "/":
                return target
            continue
        if path == allowed or path.startswith(allowed.rstrip("/") + "/"):
            return target
    return default
