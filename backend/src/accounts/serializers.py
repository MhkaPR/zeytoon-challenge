"""Input validation (Pydantic boundary schemas) and DRF output serializers."""

from pydantic import BaseModel, Field, field_validator
from rest_framework import serializers

from accounts.validation import normalize_phone


class OtpRequestInput(BaseModel):
    """Boundary schema for an OTP request."""

    phone_number: str = Field(min_length=3, max_length=32)

    @field_validator("phone_number")
    @classmethod
    def _validate_phone(cls, value):
        if normalize_phone(value) is None:
            raise ValueError("invalid_phone")
        return value


class OtpVerifyInput(BaseModel):
    """Boundary schema for an OTP verification."""

    phone_number: str = Field(min_length=3, max_length=32)
    code: str = Field(min_length=1, max_length=12)
    return_url: str | None = Field(default=None, max_length=2048)

    @field_validator("phone_number")
    @classmethod
    def _validate_phone(cls, value):
        if normalize_phone(value) is None:
            raise ValueError("invalid_phone")
        return value


def parse_input(schema_cls, data):
    """Validate ``data`` against a Pydantic schema, raising ``ApiError`` on failure."""
    from accounts.exceptions import ApiError

    try:
        return schema_cls.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise ApiError("invalid_phone", "The phone number is not valid.") from exc


# --- DRF serializers (also used to document the OpenAPI schema) -------------


class OtpRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class OtpRequestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    expires_in_seconds = serializers.IntegerField()


class OtpVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()
    return_url = serializers.CharField(required=False, allow_blank=True)


class UserIdentitySerializer(serializers.Serializer):
    phone_masked = serializers.CharField()
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
