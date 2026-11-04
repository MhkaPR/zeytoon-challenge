"""Operator-side reads for notifications, recipients, and deliveries (T036, FR-041)."""

from django.contrib import admin

from apps.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationRecipient,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("event_type", "severity", "subject", "is_resolved", "created_at")
    list_filter = ("event_type", "severity", "is_resolved")
    search_fields = ("subject", "dedup_key")


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "recipient", "channel", "state", "sent_at")
    list_filter = ("channel", "state")
