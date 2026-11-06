from rest_framework import serializers


class PublicPlanSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    domain = serializers.CharField()
    company_name = serializers.CharField()
    plan_type = serializers.CharField()
    values = serializers.DictField()
    url = serializers.CharField(allow_null=True, required=False)
    published_at = serializers.DateTimeField(allow_null=True, required=False)


class PlanFacetsSerializer(serializers.Serializer):
    companies = serializers.ListField(child=serializers.CharField())
    operating_systems = serializers.ListField(child=serializers.CharField())
    locations = serializers.ListField(child=serializers.CharField())
    resources = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    resource_units = serializers.DictField(child=serializers.CharField())


class PublicCompanySerializer(serializers.Serializer):
    domain = serializers.CharField()
    company_name = serializers.CharField()
    plan_count = serializers.IntegerField()
