"""Domain test: implicit signup inside the login flow (spec FR-005)."""

import pytest

from accounts import services
from accounts.models import User

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
