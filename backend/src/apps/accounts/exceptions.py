"""Shared API error shape and DRF exception handler.

Every error response has the shape ``{"error": {"code", "message", "fields"}}`` (see
contracts/auth-api.md).
"""

from rest_framework import status
from rest_framework.exceptions import APIException, Throttled
from rest_framework.views import exception_handler as drf_exception_handler


class ApiError(APIException):
    """Domain error carrying an explicit machine-readable ``code``."""

    def __init__(
        self, code, message, http_status=status.HTTP_400_BAD_REQUEST, fields=None
    ):
        self.code = code
        self.message = message
        self.fields = fields or {}
        super().__init__(message)
        self.status_code = http_status


def error_body(code, message, fields=None):
    return {"error": {"code": code, "message": message, "fields": fields or {}}}


def api_exception_handler(exc, context):
    """Wrap DRF exceptions in the shared error shape."""
    response = drf_exception_handler(exc, context)

    if isinstance(exc, ApiError):
        response.data = error_body(exc.code, exc.message, exc.fields)
        return response

    if response is None:
        return None

    if isinstance(exc, Throttled):
        retry_after = getattr(exc, "wait", None)
        fields = {}
        if retry_after is not None:
            fields["retry_after_seconds"] = int(retry_after)
        response.data = error_body(
            "rate_limited", "Too many requests. Please try again later.", fields
        )
        return response

    code = "invalid_request" if response.status_code < 500 else "server_error"
    detail = response.data
    if isinstance(detail, dict) and "detail" in detail:
        detail = detail["detail"]
    response.data = error_body(code, str(detail))
    return response
