"""Contract tests for token refresh and logout (contracts/auth-api.md)."""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

VERIFY_URL = "/api/v1/auth/otp/verify"
REFRESH_URL = "/api/v1/auth/token/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
PHONE = "+989123456789"


def _login(api_client, issued_code):
    code = issued_code(PHONE)
    response = api_client.post(
        VERIFY_URL, {"phone_number": PHONE, "code": code}, format="json"
    )
    return response


def test_refresh_rotates_access_token(issued_code):
    client = APIClient()
    _login(client, issued_code)
    response = client.post(REFRESH_URL, format="json")
    assert response.status_code == 200
    assert response.data["access_token"]
    assert response.cookies["refresh_token"].value


def test_refresh_without_cookie_is_unauthorized(api_client):
    response = api_client.post(REFRESH_URL, format="json")
    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_token"


def test_logout_clears_cookie_and_revokes(issued_code):
    client = APIClient()
    _login(client, issued_code)
    response = client.post(LOGOUT_URL, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


def test_logout_without_session_is_ok(api_client):
    response = api_client.post(LOGOUT_URL, format="json")
    assert response.status_code == 200
