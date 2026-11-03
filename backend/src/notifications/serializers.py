"""Pydantic inputs and DRF output serializers for the notifications API."""

from pydantic import BaseModel
from rest_framework import serializers

from notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationRecipient,
)


def parse_input(schema_cls, data):
    """Validate ``data`` against a Pydantic schema, raising the shared error shape."""
    from accounts.exceptions import ApiError

    try:
        return schema_cls.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise ApiError(
            "invalid_field",
            "Some mandatory fields are missing or invalid.",
            fields={"detail": str(exc)},
        ) from exc


class NotificationRecipientInput(BaseModel):
    user_id: int
    name: str | None = None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "event_type",
            "severity",
            "subject",
            "body",
            "related_object",
            "dedup_key",
            "is_resolved",
            "created_at",
        )


class RecipientSerializer(serializers.ModelSerializer):
    user_phone = serializers.SerializerMethodField()

    class Meta:
        model = NotificationRecipient
        fields = ("id", "user_id", "name", "is_active", "user_phone", "created_at")

    def get_user_phone(self, obj):
        return getattr(obj.user, "phone_number", "") or ""
