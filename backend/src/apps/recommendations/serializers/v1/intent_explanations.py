"""Serializers for per-cluster intent explanations."""

from rest_framework import serializers


class IntentConfidenceSerializer(serializers.Serializer):
    lift = serializers.FloatField()
    p = serializers.FloatField()
    mcc = serializers.FloatField()


class ClusterIntentExplanationSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField()
    representative_plan_id = serializers.IntegerField(allow_null=True)
    plan_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    intent = serializers.CharField()
    direction = serializers.CharField(allow_null=True, required=False)
    message = serializers.CharField()
    confidence = IntentConfidenceSerializer(allow_null=True, required=False)
