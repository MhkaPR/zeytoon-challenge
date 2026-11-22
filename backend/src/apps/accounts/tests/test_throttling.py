"""Tests for rate limiting and DoS protection (spec FR-019, FR-020, SC-008)."""

import pytest
from django.core.cache import cache
from constance.test import override_config

from apps.accounts import throttles

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/otp/request"
PHONE = "+989123456789"


def test_otp_request_throttle_returns_429_with_retry_after(api_client):
    cache.clear()
    for _ in range(2):
        api_client.post(URL, {"phone_number": PHONE}, format="json")
    response = api_client.post(URL, {"phone_number": PHONE}, format="json")

    assert response.status_code == 429
    assert response.data["error"]["code"] == "rate_limited"


def test_source_throttle_key_uses_ip_and_user_agent():
    class _Req:
        META = {"REMOTE_ADDR": "1.2.3.4", "HTTP_USER_AGENT": "pytest"}

    assert throttles._client_source(_Req()) == "1.2.3.4:pytest"


@override_config(REQUEST_COOLDOWN_SECONDS=60)
def test_otp_request_enforces_configured_cooldown(api_client, settings):
    from apps.accounts.sms import CapturingSmsGateway

    settings.THROTTLE_OTP_SOURCE = "120/hour"

    first = api_client.post(URL, {"phone_number": PHONE}, format="json")
    second = api_client.post(URL, {"phone_number": PHONE}, format="json")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.data["error"]["code"] == "rate_limited"
    assert int(second.data["error"]["fields"]["retry_after_seconds"]) > 0
    assert len(CapturingSmsGateway.sent) == 1


@override_config(REQUEST_COOLDOWN_SECONDS=1, REQUEST_HOURLY_CAP=2)
def test_otp_request_enforces_hourly_cap(api_client, settings):
    from freezegun import freeze_time
    from apps.accounts.sms import CapturingSmsGateway

    settings.THROTTLE_OTP_SOURCE = "120/hour"
    with freeze_time() as frozen_time:
        first = api_client.post(URL, {"phone_number": PHONE}, format="json")
        frozen_time.tick(delta=2)
        second = api_client.post(URL, {"phone_number": PHONE}, format="json")
        frozen_time.tick(delta=2)
        third = api_client.post(URL, {"phone_number": PHONE}, format="json")

    assert [first.status_code, second.status_code, third.status_code] == [200, 200, 429]
    assert third.data["error"]["code"] == "rate_limited"
    assert len(CapturingSmsGateway.sent) == 1


def test_regression_token_refresh_is_not_source_throttled():
    """Bug: ``/token/refresh`` shared the OTP per-source budget, so ordinary page loads
    (which refresh on every reload) exhausted the 30/hour OTP limit and locked the user out.
    """
    from apps.accounts.views.v1.accounts import TokenRefreshViewSet as TokenRefreshView

    assert throttles.OtpSourceThrottle not in TokenRefreshView.throttle_classes
