"""Operator-side read views for the console pipeline (Principle II)."""

from django.contrib import admin

from apps.pipeline.models import (
    CaptureSession,
    ClassificationRegex,
    ChangeRecord,
    ExtractedTable,
    FailureAlert,
    Link,
    LlmCostLedger,
    PlanRecord,
    ReplayRun,
    SemanticLabel,
    Site,
    TableClassification,
    Trace,
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "company", "maintenance_state")
    list_filter = ("maintenance_state",)


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ("url", "site", "review_state", "pipeline_stage", "failure_rate")
    list_filter = ("review_state", "pipeline_stage", "source")
    search_fields = ("url",)


@admin.register(CaptureSession)
class CaptureSessionAdmin(admin.ModelAdmin):
    list_display = ("link", "mode", "state", "duration_ms", "created_at")
    list_filter = ("mode", "state")


@admin.register(Trace)
class TraceAdmin(admin.ModelAdmin):
    list_display = ("storage_key", "link", "origin", "captured_at")
    list_filter = ("origin", "is_valid_trace")


@admin.register(ExtractedTable)
class ExtractedTableAdmin(admin.ModelAdmin):
    list_display = ("link", "table_index", "row_count", "column_count", "score")


@admin.register(TableClassification)
class TableClassificationAdmin(admin.ModelAdmin):
    list_display = ("table", "is_price_table", "matching_rows")
    list_filter = ("is_price_table",)


@admin.register(ClassificationRegex)
class ClassificationRegexAdmin(admin.ModelAdmin):
    list_display = ("kind", "pattern", "is_active", "description")
    list_filter = ("kind", "is_active")
    search_fields = ("pattern", "description")


@admin.register(PlanRecord)
class PlanRecordAdmin(admin.ModelAdmin):
    list_display = ("link", "plan_type", "natural_key", "confidence")


@admin.register(SemanticLabel)
class SemanticLabelAdmin(admin.ModelAdmin):
    list_display = ("table", "column", "label", "provider", "model")


@admin.register(ReplayRun)
class ReplayRunAdmin(admin.ModelAdmin):
    list_display = ("link", "state", "reextracted", "stats_applied", "started_at")
    list_filter = ("state", "reextracted")


@admin.register(ChangeRecord)
class ChangeRecordAdmin(admin.ModelAdmin):
    list_display = ("replay_run", "change_kind", "touches_price_table")
    list_filter = ("change_kind", "touches_price_table")


@admin.register(FailureAlert)
class FailureAlertAdmin(admin.ModelAdmin):
    list_display = ("link", "state", "failure_rate", "raised_at", "resolved_at")
    list_filter = ("state",)


@admin.register(LlmCostLedger)
class LlmCostLedgerAdmin(admin.ModelAdmin):
    list_display = ("scope", "period", "token_budget", "tokens_used", "stage")
    list_filter = ("scope", "period", "stage")
