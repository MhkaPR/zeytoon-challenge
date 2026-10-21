"""Input validation (Pydantic boundary schemas) and DRF output serializers."""

from pydantic import BaseModel, Field, field_validator

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
