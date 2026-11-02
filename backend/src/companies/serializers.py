"""Pydantic boundary schemas and DRF output serializers for the companies API."""

from pydantic import BaseModel, Field
from rest_framework import serializers


class CompanyInformationInput(BaseModel):
    """Boundary schema for the company-information step (FR-002, FR-003)."""

    domain: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    representative_name: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(min_length=3, max_length=32)
    internal_number: str | None = Field(default=None, max_length=32)


def parse_input(schema_cls, data):
    """Validate ``data`` against a Pydantic schema or a DRF serializer.

    Raises ``invalid_field`` (Pydantic) or ``invalid_request`` (DRF) with the offending
    fields named in ``fields`` (FR-003).
    """
    from accounts.exceptions import ApiError

    if isinstance(schema_cls, type) and issubclass(schema_cls, serializers.Serializer):
        serializer = schema_cls(data=data)
        if not serializer.is_valid():
            raise ApiError(
                "invalid_field",
                "Some fields are missing or invalid.",
                fields={"fields": list(serializer.errors.keys())},
            )
        return serializer.validated_data

    try:
        return schema_cls.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise ApiError(
            "invalid_field",
            "Some mandatory fields are missing or invalid.",
            fields={"detail": str(exc)},
        ) from exc


# --- DRF serializers (also used to document the OpenAPI schema) -------------


class CompanyInformationSerializer(serializers.Serializer):
    domain = serializers.CharField()
    company_name = serializers.CharField()
    representative_name = serializers.CharField()
    phone_number = serializers.CharField()
    internal_number = serializers.CharField(required=False, allow_blank=True)


class CompanySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    domain = serializers.CharField()
    company_name = serializers.CharField()
    representative_name = serializers.CharField()
    phone_number = serializers.CharField()
    internal_number = serializers.CharField()
    verification_status = serializers.CharField()
    is_archived = serializers.BooleanField()
    unverified = serializers.BooleanField()


class StepProgressSerializer(serializers.Serializer):
    step_key = serializers.CharField()
    order = serializers.IntegerField()
    state = serializers.CharField()
    completed = serializers.BooleanField()


class VerificationDecisionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "not_approved"])
    note = serializers.CharField(required=False, allow_blank=True)


class ErrorSerializer(serializers.Serializer):
    """Error body shape (matches the shared ``accounts`` error contract).

    Named ``CompanyError`` in the OpenAPI schema to avoid a component-name clash with the
    ``accounts`` module's ``ErrorSerializer``.
    """

    class Meta:
        ref_name = "CompanyError"

    error = serializers.DictField()


class CompanyDetailSerializer(serializers.Serializer):
    company = CompanySerializer()
    step_progress = StepProgressSerializer(many=True)
    current_step = serializers.CharField(allow_null=True)


class PanelEntrySerializer(serializers.Serializer):
    view = serializers.CharField()
    company = CompanySerializer()
    step_progress = StepProgressSerializer(many=True, required=False)
    current_step = serializers.CharField(allow_null=True, required=False)
    verification_status = serializers.CharField(required=False)


class PanelSwitcherEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    company_name = serializers.CharField()
    verification_status = serializers.CharField()
    unverified = serializers.BooleanField()


class PanelSwitcherSerializer(serializers.Serializer):
    companies = PanelSwitcherEntrySerializer(many=True)
    empty_state = serializers.BooleanField()
    message = serializers.CharField(required=False)


class VerificationDecisionResponseSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    verification_status = serializers.CharField()
    current_step = serializers.CharField(allow_null=True)
    decision = serializers.DictField()


class PlanEligibilitySerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    missing = serializers.ListField(child=serializers.CharField())
    message = serializers.CharField(required=False)
