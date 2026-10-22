"""Contract tests for GET /api/v1/auth/session (contracts/auth-api.md)."""

import pytest

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/session"
VERIFY_URL = "/api/v1/auth/otp/verify"
PHONE = "+989123456789"


def test_session_is_guest_without_token(api_client):
    response = api_client.get(URL)
    assert response.status_code == 200
    assert response.data == {"authenticated": False, "role": "guest"}


def test_session_returns_user_with_token(api_client, issued_code):
    code = issued_code(PHONE)
    login = api_client.post(
        VERIFY_URL, {"phone_number": PHONE, "code": code}, format="json"
    )
    access = login.data["access_token"]
    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {access}")
    assert response.status_code == 200
    assert response.data["authenticated"] is True
    assert response.data["user"]["role"] == "regular"
