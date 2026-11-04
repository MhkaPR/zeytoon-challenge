"""Operator-side read-only registration for published plan records (T036)."""

from django.contrib import admin

from apps.catalog.models import PublishedRecord


@admin.register(PublishedRecord)
class PublishedRecordAdmin(admin.ModelAdmin):
    list_display = (
        "natural_key",
        "plan_type",
        "site",
        "link",
        "is_published",
        "published_at",
    )
    list_filter = ("plan_type", "source", "is_published")
    search_fields = ("natural_key",)
    readonly_fields = ("created_at", "updated_at")
