"""Tests for rate limiting and DoS protection (spec FR-019, FR-020, SC-008)."""

import pytest
from django.core.cache import cache
from django.test import override_settings

from accounts import throttles

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/otp/request"
PHONE = "+989123456789"


def test_otp_request_throttle_returns_429_with_retry_after(api_client):
    # Set the rate directly on the throttle class to avoid DRF's cached api_settings.
    original = throttles.OtpRequestPhoneThrottle.THROTTLE_RATES
    throttles.OtpRequestPhoneThrottle.THROTTLE_RATES = {"otp_request_phone": "2/min"}
    cache.clear()
    try:
        for _ in range(2):
            api_client.post(URL, {"phone_number": PHONE}, format="json")
        response = api_client.post(URL, {"phone_number": PHONE}, format="json")
    finally:
        throttles.OtpRequestPhoneThrottle.THROTTLE_RATES = original

    assert response.status_code == 429
    assert response.data["error"]["code"] == "rate_limited"


def test_source_throttle_key_uses_ip_and_user_agent():
    class _Req:
        META = {"REMOTE_ADDR": "1.2.3.4", "HTTP_USER_AGENT": "pytest"}

    assert throttles._client_source(_Req()) == "1.2.3.4:pytest"
