"""Domain test: implicit signup inside the login flow (spec FR-005)."""

import pytest

from apps.accounts import services
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


def test_first_login_creates_user(issued_code):
    code = issued_code(PHONE)
    assert not User.objects.filter(phone_number=PHONE).exists()
    services.verify_otp(PHONE, code)
    assert User.objects.filter(phone_number=PHONE).count() == 1


def test_second_login_reuses_user(issued_code):
    code = issued_code(PHONE)
    services.verify_otp(PHONE, code)
    code = issued_code(PHONE)
    services.verify_otp(PHONE, code)
    assert User.objects.filter(phone_number=PHONE).count() == 1


def test_implicit_user_has_unusable_password(issued_code):
    """OTP users have no password; the stored value must not be usable (spec FR-005)."""
    code = issued_code(PHONE)
    services.verify_otp(PHONE, code)

    user = User.objects.get(phone_number=PHONE)
    assert user.password.startswith("!")
    assert user.has_usable_password() is False


def test_password_check_never_succeeds_for_otp_user(issued_code):
    """No candidate password (including the empty string) can authenticate an OTP user."""
    code = issued_code(PHONE)
    services.verify_otp(PHONE, code)

    user = User.objects.get(phone_number=PHONE)
    assert user.check_password("") is False
    assert user.check_password("anything") is False
