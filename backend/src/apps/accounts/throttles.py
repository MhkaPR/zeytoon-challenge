"""DRF throttle classes for the OTP endpoints.

Per-phone and per-source limits protect against abuse and DoS (spec FR-019, FR-020). Rates
are configured in settings (``DEFAULT_THROTTLE_RATES``) so they stay out of code.
"""

from rest_framework.throttling import SimpleRateThrottle


def _client_source(request):
    """Best-effort source identifier (IP plus user-agent)."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    if not ip:
        ip = request.META.get("REMOTE_ADDR", "")
    ua = request.META.get("HTTP_USER_AGENT", "")
    return f"{ip}:{ua[:64]}"


class OtpRequestPhoneThrottle(SimpleRateThrottle):
    scope = "otp_request_phone"

    def get_cache_key(self, request, view):
        phone = (request.data or {}).get("phone_number")
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(phone)}


class OtpVerifyPhoneThrottle(SimpleRateThrottle):
    scope = "otp_verify_phone"

    def __init__(self):
        # Apply the configurable window (VERIFY_WINDOW_SECONDS / VERIFY_WINDOW_LIMIT) so the
        # values stay out of code (Constitution Principle XIII). DRF's parse_rate only
        # accepts single-character periods, so the numbers are set directly.
        super().__init__()
        from constance import config

        self.num_requests = int(config.VERIFY_WINDOW_LIMIT)
        self.duration = int(config.VERIFY_WINDOW_SECONDS)

    def get_cache_key(self, request, view):
        phone = (request.data or {}).get("phone_number")
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(phone)}


class OtpSourceThrottle(SimpleRateThrottle):
    scope = "otp_source"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": _client_source(request),
        }
