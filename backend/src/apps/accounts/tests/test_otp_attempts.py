"""Domain test: failed-attempt counting and code invalidation (spec FR-016)."""

import pytest
from constance.test import override_config

from apps.accounts import services, state
from apps.accounts.exceptions import ApiError

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


@override_config(MAX_VERIFY_ATTEMPTS=3)
def test_attempts_increment_and_invalidate(issued_code):
    issued_code(PHONE)
    for _ in range(2):
        with pytest.raises(ApiError):
            services.verify_otp(PHONE, "000000")
    assert state.get_code(PHONE) is not None
    with pytest.raises(ApiError):
        services.verify_otp(PHONE, "000000")
    # Code is invalidated once the attempt threshold is reached.
    assert state.get_code(PHONE) is None


@override_config(MAX_VERIFY_ATTEMPTS=3)
def test_correct_code_after_failed_attempts_still_works(issued_code):
    code = issued_code(PHONE)
    with pytest.raises(ApiError):
        services.verify_otp(PHONE, "000000")
    result = services.verify_otp(PHONE, code)
    assert result["user"].phone_number == PHONE
