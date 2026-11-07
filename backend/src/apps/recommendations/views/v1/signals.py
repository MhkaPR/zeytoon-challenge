"""Signal endpoint: the only client-initiated recommendation action."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema

from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.interfaces import RecommendationsInterface
from apps.recommendations.serializers.v1.signals import (
    SignalRequestSerializer,
    SignalResponseSerializer,
)


class SignalThrottle(SimpleRateThrottle):
    """Per-identity throttle in addition to the recorder's per-viewer cap."""

    scope = "recommendation_signal"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"u{request.user.pk}"
        else:
            ident = f"v{request.COOKIES.get('visitor_id', '') or self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class SignalViewSet(GenericViewSet):
    authentication_classes = []
    throttle_classes = [SignalThrottle]

    @extend_schema(
        request=SignalRequestSerializer,
        responses={200: SignalResponseSerializer},
    )
    def create(self, request):
        serializer = SignalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        records = CatalogInterface.published_plan_records()
        result = RecommendationsInterface.record_signals(
            records,
            payload["kind"],
            payload["plan_ids"],
            query=payload.get("query", ""),
            visitor_id=request.COOKIES.get("visitor_id"),
            user=request.user if request.user.is_authenticated else None,
        )
        return Response(
            {"data": SignalResponseSerializer(result).data},
            status=status.HTTP_200_OK,
        )
