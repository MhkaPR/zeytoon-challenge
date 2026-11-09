"""Contract tests for POST /api/v1/auth/otp/request (contracts/auth-api.md)."""

import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/otp/request"


def test_request_returns_sent_with_expiry(api_client):
    response = api_client.post(URL, {"phone_number": "+989123456789"}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "sent"
    assert response.data["expires_in_seconds"] > 0


def test_request_rejects_invalid_phone(api_client):
    response = api_client.post(URL, {"phone_number": "123"}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_phone"


def test_request_rejects_blocked_user(api_client, role_groups):
    User.objects.create_user(
        username="+989121112233",
        phone_number="+989121112233",
        password="x",
        status=User.Status.BLOCKED,
    )
    response = api_client.post(URL, {"phone_number": "+989121112233"}, format="json")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "user_blocked"
    assert response.data["error"]["fields"]["channels"]
