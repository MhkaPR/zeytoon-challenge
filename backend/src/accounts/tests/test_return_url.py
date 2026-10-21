"""Domain test: return-URL validation and fallback (spec FR-011)."""

import pytest
from constance.test import override_config

from accounts.services import resolve_return_url

pytestmark = pytest.mark.django_db


@override_config(
    RETURN_URL_ALLOWLIST=["/", "/plans", "/compare"],
    DEFAULT_RETURN_PATH="/",
)
def test_allowlisted_path_is_honored():
    assert resolve_return_url("/plans/compare?ids=1,2") == "/plans/compare?ids=1,2"


@override_config(
    RETURN_URL_ALLOWLIST=["/", "/plans"],
    DEFAULT_RETURN_PATH="/",
)
def test_external_url_falls_back():
    assert resolve_return_url("https://evil.example.com/steal") == "/"


@override_config(
    RETURN_URL_ALLOWLIST=["/", "/plans"],
    DEFAULT_RETURN_PATH="/",
)
def test_unknown_path_falls_back():
    assert resolve_return_url("/admin/secret") == "/"


@override_config(RETURN_URL_ALLOWLIST=["/"], DEFAULT_RETURN_PATH="/")
def test_protocol_relative_falls_back():
    assert resolve_return_url("//evil.example.com") == "/"
