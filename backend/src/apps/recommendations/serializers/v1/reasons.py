"""Serializers for per-cluster recommendation reasons."""

from rest_framework import serializers


class ReasonSerializer(serializers.Serializer):
    feature = serializers.CharField()
    type = serializers.ChoiceField(choices=["numeric", "categorical", "textual"])
    f1 = serializers.FloatField()
    unit = serializers.CharField(required=False, allow_null=True)
    label = serializers.CharField(required=False, allow_null=True)
    real_range = serializers.ListField(
        child=serializers.FloatField(), required=False, min_length=2, max_length=2
    )


class ClusterExplanationSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField()
    representative_plan_id = serializers.IntegerField(allow_null=True)
    reasons = ReasonSerializer(many=True)
