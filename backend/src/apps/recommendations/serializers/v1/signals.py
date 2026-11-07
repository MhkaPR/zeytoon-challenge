"""Serializers for the signal endpoint."""

from rest_framework import serializers

from apps.recommendations.models import InterestSignal


class SignalRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=InterestSignal.Kind.choices)
    plan_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    query = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        if (
            attrs["kind"] == InterestSignal.Kind.SEARCH_IMPRESSION
            and not attrs.get("query", "").strip()
        ):
            raise serializers.ValidationError(
                {"query": "A search impression requires the typed query."}
            )
        return attrs


class SignalResponseSerializer(serializers.Serializer):
    accepted = serializers.IntegerField()
    ignored = serializers.IntegerField()
    profile = serializers.CharField()
