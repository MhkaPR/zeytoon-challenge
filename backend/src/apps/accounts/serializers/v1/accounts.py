"""DRF input and output serializers for the authentication API."""

from rest_framework import serializers

from accounts.validation import normalize_phone
from utils.serializers import parse_input


def _invalid_phone(code="invalid_phone", message="The phone number is not valid."):
    """Return a DRF validator that raises the shared ``ApiError`` contract."""
    from accounts.exceptions import ApiError

    def validator(value):
        if normalize_phone(value) is None:
            raise ApiError(code, message)
        return value

    return validator


class OtpRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)

    def validate_phone_number(self, value):
        if normalize_phone(value) is None:
            from accounts.exceptions import ApiError

            raise ApiError("invalid_phone", "The phone number is not valid.")
        return value


class OtpRequestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    expires_in_seconds = serializers.IntegerField()


class OtpVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=12)
    return_url = serializers.CharField(required=False, allow_blank=True)

    def validate_phone_number(self, value):
        if normalize_phone(value) is None:
            from accounts.exceptions import ApiError

            raise ApiError("invalid_phone", "The phone number is not valid.")
        return value


class UserIdentitySerializer(serializers.Serializer):
    phone = serializers.CharField()
    role = serializers.CharField()


class OtpVerifyResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    redirect_to = serializers.CharField()
    user = UserIdentitySerializer()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()


class StatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class SessionResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    role = serializers.CharField(required=False)
    user = UserIdentitySerializer(required=False)


class ErrorSerializer(serializers.Serializer):
    error = serializers.DictField()


__all__ = [
    "parse_input",
    "OtpRequestSerializer",
    "OtpRequestResponseSerializer",
    "OtpVerifySerializer",
    "OtpVerifyResponseSerializer",
    "TokenRefreshResponseSerializer",
    "StatusSerializer",
    "SessionResponseSerializer",
    "UserIdentitySerializer",
    "ErrorSerializer",
]
