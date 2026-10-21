"""Contract tests for POST /api/v1/auth/otp/verify (contracts/auth-api.md)."""

import pytest

from accounts import state

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/otp/verify"
PHONE = "+989123456789"


def test_verify_success_returns_tokens_and_redirect(api_client, issued_code):
    code = issued_code(PHONE)
    response = api_client.post(
        URL, {"phone_number": PHONE, "code": code, "return_url": "/plans"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["token_type"] == "Bearer"
    assert response.data["access_token"]
    assert response.data["redirect_to"] == "/plans"
    assert "***" in response.data["user"]["phone_masked"]


def test_verify_wrong_code_message(api_client, issued_code):
    issued_code(PHONE)
    response = api_client.post(
        URL, {"phone_number": PHONE, "code": "000000"}, format="json"
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "otp_incorrect"
    assert response.data["error"]["message"] == "The code is incorrect"


def test_verify_missing_code_is_incorrect(api_client):
    response = api_client.post(
        URL, {"phone_number": PHONE, "code": "123456"}, format="json"
    )
    assert response.status_code == 400
    assert response.data["error"]["message"] == "The code is incorrect"


def test_verify_blocked_user(api_client, role_groups, issued_code):
    from accounts.models import User

    User.objects.create_user(
        username=PHONE, phone_number=PHONE, password="x", status=User.Status.BLOCKED
    )
    code = issued_code(PHONE)
    response = api_client.post(
        URL, {"phone_number": PHONE, "code": code}, format="json"
    )
    assert response.status_code == 409
    assert response.data["error"]["code"] == "user_blocked"
