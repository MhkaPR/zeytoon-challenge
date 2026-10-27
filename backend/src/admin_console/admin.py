"""Operator-side read views for the console pipeline (T036, Principle II)."""

from django.contrib import admin

from admin_console.models import (
    CaptureSession,
    ExtractedTable,
    ExtractionRecipe,
    FailureAlert,
    Link,
    LlmCostLedger,
    RecipeFieldBinding,
    ReplayRun,
    SemanticLabel,
    Site,
    Trace,
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "company", "maintenance_state", "has_sitemap")
    list_filter = ("maintenance_state", "has_sitemap")


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ("url", "site", "review_state", "pipeline_stage", "failure_rate")
    list_filter = ("review_state", "pipeline_stage", "source")
    search_fields = ("url", "url_hash")


@admin.register(CaptureSession)
class CaptureSessionAdmin(admin.ModelAdmin):
    list_display = ("link", "operator", "mode", "state", "created_at")
    list_filter = ("mode", "state")


@admin.register(Trace)
class TraceAdmin(admin.ModelAdmin):
    list_display = ("storage_key", "link", "origin", "byte_size", "captured_at")
    list_filter = ("origin", "is_valid_trace")


@admin.register(ExtractedTable)
class ExtractedTableAdmin(admin.ModelAdmin):
    list_display = ("link", "table_index", "row_count", "column_count", "score")


@admin.register(SemanticLabel)
class SemanticLabelAdmin(admin.ModelAdmin):
    list_display = ("table", "column", "label", "provider", "model")


@admin.register(ExtractionRecipe)
class ExtractionRecipeAdmin(admin.ModelAdmin):
    list_display = ("link", "plan_type", "version", "is_current", "is_complete")
    list_filter = ("plan_type", "is_current", "is_complete")


@admin.register(RecipeFieldBinding)
class RecipeFieldBindingAdmin(admin.ModelAdmin):
    list_display = ("recipe", "schema_field_key", "selector", "formula")


@admin.register(ReplayRun)
class ReplayRunAdmin(admin.ModelAdmin):
    list_display = ("link", "state", "stats_applied", "stats_failed", "started_at")
    list_filter = ("state",)


@admin.register(FailureAlert)
class FailureAlertAdmin(admin.ModelAdmin):
    list_display = ("link", "state", "failure_rate", "raised_at", "resolved_at")
    list_filter = ("state",)


@admin.register(LlmCostLedger)
class LlmCostLedgerAdmin(admin.ModelAdmin):
    list_display = ("scope", "ceiling_amount", "period", "amount", "timestamp")
