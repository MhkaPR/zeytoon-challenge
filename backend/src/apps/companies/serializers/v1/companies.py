"""Pydantic boundary schemas and DRF serializers for the companies API."""

from pydantic import BaseModel, Field
from rest_framework import serializers

from apps.companies.models import Company, CompanyStepProgress


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
    from apps.accounts.exceptions import ApiError

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


class CompanySerializer(serializers.ModelSerializer):
    unverified = serializers.BooleanField(source="is_unverified", read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "domain",
            "company_name",
            "representative_name",
            "phone_number",
            "internal_number",
            "verification_status",
            "is_archived",
            "unverified",
        )


class StepProgressSerializer(serializers.ModelSerializer):
    completed = serializers.SerializerMethodField()

    class Meta:
        model = CompanyStepProgress
        fields = ("step_key", "order", "state", "completed")

    def get_completed(self, obj):
        return obj.state in {
            CompanyStepProgress.State.APPROVED,
            CompanyStepProgress.State.SAVED,
        }


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


class CompanyRegistrationSerializer(serializers.Serializer):
    company = CompanySerializer()
    step_progress = StepProgressSerializer(many=True)


class CompanyListSerializer(serializers.Serializer):
    companies = CompanySerializer(many=True)


class PanelEntrySerializer(serializers.Serializer):
    view = serializers.CharField()
    company = CompanySerializer()
    step_progress = StepProgressSerializer(many=True, required=False)
    current_step = serializers.CharField(allow_null=True, required=False)
    verification_status = serializers.CharField(required=False)


class PanelSwitcherEntrySerializer(serializers.ModelSerializer):
    unverified = serializers.BooleanField(source="is_unverified", read_only=True)

    class Meta:
        model = Company
        fields = ("id", "company_name", "verification_status", "unverified")


class PanelSwitcherSerializer(serializers.Serializer):
    companies = PanelSwitcherEntrySerializer(many=True)
    empty_state = serializers.BooleanField()
    message = serializers.CharField(required=False)


class StepAbandonSerializer(serializers.Serializer):
    step_key = serializers.CharField()
    resume_at = serializers.CharField(allow_null=True)
    drafts_cleared = serializers.ListField(child=serializers.CharField())


class VerificationDecisionSerializer(serializers.Serializer):
    outcome = serializers.CharField()
    actor_id = serializers.IntegerField()
    decided_at = serializers.CharField()
    note = serializers.CharField()


class VerificationDecisionResponseSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    verification_status = serializers.CharField()
    current_step = serializers.CharField(allow_null=True)
    decision = VerificationDecisionSerializer()


class PlanEligibilitySerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    missing = serializers.ListField(child=serializers.CharField())
    message = serializers.CharField(required=False)


class CompanyLinksSerializer(serializers.Serializer):
    links = serializers.ListField(child=serializers.DictField())


class PendingApprovalSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    representative_name = serializers.CharField()
    domain = serializers.CharField()
    phone_number = serializers.CharField()
    registered_at = serializers.CharField()
    duplicate_domain_warning = serializers.BooleanField()
    duplicate_of = serializers.ListField(child=serializers.IntegerField())
