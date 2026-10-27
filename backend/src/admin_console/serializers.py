"""Pydantic boundary schemas and DRF output serializers for the console API."""

from pydantic import BaseModel, Field
from rest_framework import serializers


def parse_input(schema_cls, data):
    """Validate ``data`` against a Pydantic schema or DRF serializer (shared pattern)."""
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


# --- Pydantic inputs --------------------------------------------------------


class VerificationDecisionInput(BaseModel):
    outcome: str = Field(pattern="^(approved|not_approved)$")
    note: str | None = None


class SiteCreateInput(BaseModel):
    company_id: int


class ManualLinksInput(BaseModel):
    urls: list[str] = Field(default_factory=list)


class LinkReviewInput(BaseModel):
    keep_ids: list[int] = Field(default_factory=list)
    remove_ids: list[int] = Field(default_factory=list)


class CaptureStartInput(BaseModel):
    mode: str = Field(default="interactive")
    duration_ms: int | None = None


class RecipeBindingInput(BaseModel):
    schema_field_key: str
    source_table_id: int | None = None
    source_column_id: int | None = None
    selector: str = ""
    formula: str = ""
    aggregation: str = ""


class RecipeSaveInput(BaseModel):
    plan_type: str
    bindings: list[RecipeBindingInput] = Field(default_factory=list)


class ReplayRunInput(BaseModel):
    link_ids: list[int] = Field(default_factory=list)
    site_id: int | None = None


class RecipientInput(BaseModel):
    user_id: int
    name: str | None = None


class SettingsUpdateInput(BaseModel):
    values: dict = Field(default_factory=dict)


class LlmCostCeilingInput(BaseModel):
    ceiling_amount: float | None = None
    period: str = "monthly"


# --- DRF serializers (also document the OpenAPI schema) ---------------------


class ApprovalQueueEntrySerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    representative_name = serializers.CharField()
    domain = serializers.CharField()
    phone_masked = serializers.CharField()
    registered_at = serializers.CharField()
    duplicate_domain_warning = serializers.BooleanField()
    duplicate_of = serializers.ListField(child=serializers.IntegerField())


class ApprovalQueueSerializer(serializers.Serializer):
    results = ApprovalQueueEntrySerializer(many=True)
    count = serializers.IntegerField()


class VerificationDecisionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "not_approved"])
    note = serializers.CharField(required=False, allow_blank=True)


class ConsoleErrorSerializer(serializers.Serializer):
    """Error body shape (matches the shared accounts error contract)."""

    class Meta:
        ref_name = "OpsConsoleError"

    error = serializers.DictField()
