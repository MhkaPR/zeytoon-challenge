"""Public interface for the accounts module.

Other modules MUST import account behavior through this module only; direct access to the
accounts tables is forbidden (Constitution Principle VI).
"""

from apps.accounts import selectors
from apps.accounts.exceptions import ApiError
from apps.accounts.services import (
    issue_tokens,
    request_otp,
    resolve_return_url,
    revoke_tokens,
    verify_otp,
)


class AccountsInterface:
    """The single sanctioned entry point into the accounts module."""

    # --- read ---
    @staticmethod
    def current_identity(request):
        return selectors.resolve_current_user(request)

    @staticmethod
    def role_of(user):
        return selectors.get_user_role(user)

    # --- write ---
    @staticmethod
    def request_otp(phone_number, source=None):
        return request_otp(phone_number, source=source)

    @staticmethod
    def verify_otp(phone_number, code, return_url=None):
        return verify_otp(phone_number, code, return_url=return_url)

    @staticmethod
    def revoke_session(refresh_token):
        return revoke_tokens(refresh_token)

    @staticmethod
    def safe_return_url(return_url):
        return resolve_return_url(return_url)


__all__ = ["AccountsInterface", "ApiError", "issue_tokens"]
