"""Domain test: blocked/revoked users resolve as guest, not authenticated (FR-010/FR-025)."""

import pytest

from apps.accounts import selectors
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


class _FakeRequest:
    def __init__(self, token):
        self.META = {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def test_blocked_user_is_treated_as_guest(issued_code):
    from rest_framework_simplejwt.tokens import RefreshToken

    user = User.objects.create_user(username=PHONE, phone_number=PHONE, password="x")
    token = str(RefreshToken.for_user(user).access_token)
    assert selectors.resolve_current_user(_FakeRequest(token))["authenticated"] is True

    user.status = User.Status.BLOCKED
    user.save(update_fields=["status"])
    assert selectors.resolve_current_user(_FakeRequest(token)) == {
        "authenticated": False,
        "role": "guest",
    }


def test_invalid_token_is_guest():
    request = _FakeRequest("not-a-real-token")
    assert selectors.resolve_current_user(request) == {
        "authenticated": False,
        "role": "guest",
    }
