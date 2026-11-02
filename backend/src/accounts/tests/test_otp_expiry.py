"""Domain test: expired codes produce only the "incorrect" message (spec FR-015)."""

import pytest
from freezegun import freeze_time

from accounts import services, state
from accounts.exceptions import ApiError

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


def test_expired_code_is_incorrect_not_expired():
    with freeze_time("2026-01-01 12:00:00"):
        state.store_code(PHONE, "123456", ttl_seconds=60)
    with freeze_time("2026-01-01 12:05:00"):
        with pytest.raises(ApiError) as exc:
            services.verify_otp(PHONE, "123456")
    assert exc.value.code == "otp_incorrect"
    assert exc.value.message == "The code is incorrect"
    assert "expire" not in exc.value.message.lower()


def test_absent_code_is_incorrect():
    with pytest.raises(ApiError) as exc:
        services.verify_otp(PHONE, "123456")
    assert exc.value.message == "The code is incorrect"
