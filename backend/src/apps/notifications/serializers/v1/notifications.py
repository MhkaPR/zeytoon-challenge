"""DRF input and output serializers for the notifications API."""

from rest_framework import serializers

from apps.notifications.models import (
    Notification,
    NotificationRecipient,
)
from apps.utils.serializers import parse_input


class NotificationRecipientInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


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


class NotificationInboxSerializer(serializers.Serializer):
    results = NotificationSerializer(many=True)
    count = serializers.IntegerField()


class RecipientListSerializer(serializers.Serializer):
    results = RecipientSerializer(many=True)
    count = serializers.IntegerField()


__all__ = [
    "parse_input",
    "NotificationRecipientInputSerializer",
    "NotificationSerializer",
    "RecipientSerializer",
    "NotificationInboxSerializer",
    "RecipientListSerializer",
]
