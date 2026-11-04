"""Domain test: temporary lockout after repeated failures (spec FR-017)."""

import pytest
from constance.test import override_config

from apps.accounts import services, state
from apps.accounts.exceptions import ApiError

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


@override_config(
    LOCKOUT_THRESHOLD=2, MAX_VERIFY_ATTEMPTS=5, LOCKOUT_DURATION_SECONDS=900
)
def test_lockout_after_threshold_blocks_request_and_verify(issued_code):
    issued_code(PHONE)
    for _ in range(2):
        with pytest.raises(ApiError):
            services.verify_otp(PHONE, "000000")

    assert state.is_locked_out(PHONE)

    with pytest.raises(ApiError) as request_exc:
        services.request_otp(PHONE)
    assert request_exc.value.code == "locked_out"

    with pytest.raises(ApiError) as verify_exc:
        services.verify_otp(PHONE, "000000")
    assert verify_exc.value.code == "locked_out"
