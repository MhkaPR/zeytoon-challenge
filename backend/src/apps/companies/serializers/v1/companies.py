"""DRF input and output serializers for the companies API."""

from rest_framework import serializers

from apps.companies.models import Company, CompanyStepProgress
from apps.utils.serializers import parse_input


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
            "charge_status",
            "crawl_enabled",
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
    plan_eligibility = serializers.DictField(required=False)


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


class CreditEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    direction = serializers.CharField()
    amount = serializers.IntegerField()
    reason = serializers.CharField()
    reference = serializers.CharField()


class CompanyCreditSerializer(serializers.Serializer):
    current_credit = serializers.IntegerField()
    entries = CreditEntrySerializer(many=True)


class CrawlToggleInputSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()


class CrawlToggleResponseSerializer(serializers.Serializer):
    crawl_enabled = serializers.BooleanField()
    credit_unchanged = serializers.BooleanField(default=True)


class CreditMovementInputSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=["charge", "decharge"])
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(
        choices=["payment", "platform_view", "adjustment"]
    )
    reference = serializers.CharField(required=False, allow_blank=True, default="")
