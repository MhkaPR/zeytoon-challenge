"""DRF input and output serializers for the operator console API."""

from rest_framework import serializers


# --- Input serializers ------------------------------------------------------


class VerificationDecisionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "not_approved"])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class SiteCreateInputSerializer(serializers.Serializer):
    company_id = serializers.IntegerField(min_value=1)


class DiscoverLinksInputSerializer(serializers.Serializer):
    max_pages = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    max_depth = serializers.IntegerField(required=False, min_value=1, allow_null=True)


class ManualLinksInputSerializer(serializers.Serializer):
    urls = serializers.ListField(child=serializers.URLField(), allow_empty=False)


class CaptureStartInputSerializer(serializers.Serializer):
    duration_ms = serializers.IntegerField(required=False, min_value=1, allow_null=True)


class ClassifyInputSerializer(serializers.Serializer):
    table_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )


class PlansInputSerializer(serializers.Serializer):
    classification_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )


class PlanIgnoreInputSerializer(serializers.Serializer):
    ignored = serializers.BooleanField()


class ReplayRunInputSerializer(serializers.Serializer):
    link_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )
    site_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)


class SettingsUpdateInputSerializer(serializers.Serializer):
    values = serializers.DictField(required=True)


class TokenBudgetInputSerializer(serializers.Serializer):
    token_budget = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    period = serializers.ChoiceField(
        choices=["daily", "monthly", "total"], required=False, default="monthly"
    )


class CaptureFailInputSerializer(serializers.Serializer):
    error = serializers.CharField(required=False, allow_blank=True, default="failed")


# --- Output serializers -----------------------------------------------------


class ApprovalQueueEntrySerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    representative_name = serializers.CharField()
    domain = serializers.CharField()
    phone_number = serializers.CharField()
    registered_at = serializers.CharField()
    duplicate_domain_warning = serializers.BooleanField()
    duplicate_of = serializers.ListField(child=serializers.IntegerField())


class ApprovalQueueSerializer(serializers.Serializer):
    results = ApprovalQueueEntrySerializer(many=True)
    count = serializers.IntegerField()


class SiteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    company_id = serializers.IntegerField()
    domain = serializers.CharField()
    maintenance_state = serializers.CharField()
    onboarded_at = serializers.CharField(allow_null=True)


class SiteListEntrySerializer(SiteSerializer):
    company_name = serializers.CharField()
    links_count = serializers.IntegerField()
    stage_counts = serializers.DictField(child=serializers.IntegerField())


class SiteListSerializer(serializers.Serializer):
    results = SiteListEntrySerializer(many=True)
    count = serializers.IntegerField()


class LinkSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    site_id = serializers.IntegerField()
    url = serializers.CharField()
    source = serializers.CharField()
    review_state = serializers.CharField()
    pipeline_stage = serializers.CharField()
    failure_rate = serializers.FloatField()
    current_trace_id = serializers.IntegerField(allow_null=True)
    last_error = serializers.CharField(allow_blank=True, allow_null=True)
    pipeline_task_state = serializers.CharField(allow_blank=True)


class LinkListSerializer(serializers.Serializer):
    results = LinkSerializer(many=True)


class SiteDetailSerializer(serializers.Serializer):
    site = SiteSerializer()
    links = LinkSerializer(many=True)


class SiteLinksSerializer(serializers.Serializer):
    site_id = serializers.IntegerField()
    links = LinkSerializer(many=True)
    count = serializers.IntegerField()


class DiscoverLinksSerializer(serializers.Serializer):
    site = SiteSerializer()
    discovered = serializers.IntegerField()
    after_policy = serializers.IntegerField()
    candidates = LinkSerializer(many=True)


class CaptureSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    link_id = serializers.IntegerField()
    state = serializers.CharField()
    mode = serializers.CharField()
    duration_ms = serializers.IntegerField(allow_null=True)
    error = serializers.CharField(allow_blank=True, allow_null=True)
    trace_id = serializers.IntegerField(allow_null=True)


class CaptureStartSerializer(serializers.Serializer):
    capture_session = CaptureSessionSerializer()
    link = LinkSerializer()


class CaptureListSerializer(serializers.Serializer):
    results = CaptureSessionSerializer(many=True)


class CaptureFailSerializer(serializers.Serializer):
    capture_session = CaptureSessionSerializer()


class ExtractionSerializer(serializers.Serializer):
    extraction = serializers.DictField()
    link = LinkSerializer()


class TablesSerializer(serializers.Serializer):
    tables = serializers.ListField(child=serializers.DictField())


class ClassificationSerializer(serializers.Serializer):
    classifications = serializers.ListField(child=serializers.DictField())
    link = LinkSerializer(required=False)


class PlansSerializer(serializers.Serializer):
    plans = serializers.ListField(child=serializers.DictField())
    link = LinkSerializer(required=False)


class PlanIgnoreSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    ignored = serializers.BooleanField()


class LabelingSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.DictField())
    labeled_tables = serializers.IntegerField()


class PublishSerializer(serializers.Serializer):
    published = serializers.IntegerField()
    link = LinkSerializer()


class PlanSchemaFieldSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.CharField()
    required = serializers.BooleanField()
    values = serializers.ListField(child=serializers.CharField())


class PlanSchemaSerializer(serializers.Serializer):
    plan_type = serializers.CharField()
    label = serializers.CharField()
    fields = PlanSchemaFieldSerializer(many=True)


class ReplayRunSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    link_id = serializers.IntegerField()
    state = serializers.CharField()
    started_at = serializers.CharField(allow_null=True)
    finished_at = serializers.CharField(allow_null=True)
    before_trace_id = serializers.IntegerField(allow_null=True)
    after_trace_id = serializers.IntegerField(allow_null=True)
    diff_summary = serializers.DictField()
    reextracted = serializers.IntegerField(required=False)
    stats_applied = serializers.IntegerField()
    stats_skipped = serializers.IntegerField()
    stats_failed = serializers.IntegerField()
    changes = serializers.ListField(child=serializers.DictField(), required=False)


class ReplayRunListSerializer(serializers.Serializer):
    results = ReplayRunSerializer(many=True)


class ReplayEnqueueSerializer(serializers.Serializer):
    enqueued = serializers.IntegerField()


class AlertSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    link_id = serializers.IntegerField()
    state = serializers.CharField()
    failure_rate = serializers.FloatField()
    raised_at = serializers.CharField(allow_null=True)
    resolved_at = serializers.CharField(allow_null=True)


class AlertListSerializer(serializers.Serializer):
    results = AlertSerializer(many=True)


class LinkFailureSerializer(serializers.Serializer):
    link_id = serializers.IntegerField()
    failure_rate = serializers.FloatField()
    window_runs = serializers.IntegerField()
    threshold = serializers.FloatField()
    alert_state = serializers.CharField()


class RerunSerializer(serializers.Serializer):
    link = LinkSerializer()
    queued = serializers.BooleanField()


class SettingsSerializer(serializers.Serializer):
    values = serializers.DictField()


class TokenBudgetSerializer(serializers.Serializer):
    scope = serializers.CharField()
    period = serializers.CharField()
    token_budget = serializers.IntegerField(allow_null=True)
    tokens_used = serializers.IntegerField()


class MetricsSerializer(serializers.Serializer):
    links_total = serializers.IntegerField()
    links_published = serializers.IntegerField()
    links_awaiting_budget = serializers.IntegerField()
    links_dead_lettered = serializers.IntegerField()
    open_alerts = serializers.IntegerField()
    published_records = serializers.IntegerField()
    llm_tokens_used = serializers.IntegerField()


class VerificationDecisionResultSerializer(serializers.Serializer):
    company = serializers.DictField()
    decision = serializers.DictField()
    site = SiteSerializer(allow_null=True)


class ConsoleErrorSerializer(serializers.Serializer):
    error = serializers.DictField()


# Backwards-compatible aliases used by the views.
VerificationDecisionInput = VerificationDecisionInputSerializer
SiteCreateInput = SiteCreateInputSerializer
DiscoverLinksInput = DiscoverLinksInputSerializer
ManualLinksInput = ManualLinksInputSerializer
CaptureStartInput = CaptureStartInputSerializer
ClassifyInput = ClassifyInputSerializer
PlansInput = PlansInputSerializer
PlanIgnoreInput = PlanIgnoreInputSerializer
ReplayRunInput = ReplayRunInputSerializer
SettingsUpdateInput = SettingsUpdateInputSerializer
TokenBudgetInput = TokenBudgetInputSerializer
