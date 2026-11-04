"""Read-only public API for currently published plans."""

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.admin_console.interfaces import AdminConsoleInterface
from apps.catalog.filters import PublishedPlanFilter
from apps.catalog.models import PublishedRecord
from apps.core.site_config import public_site_config


class SiteConfigViewSet(GenericViewSet):
    """Public runtime configuration consumed by the frontend SPA."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="site-config")
    def site_config(self, request):
        return Response(public_site_config())


class PublishedPlansViewSet(ListModelMixin, GenericViewSet):
    authentication_classes = []
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = PublishedPlanFilter
    queryset = PublishedRecord.objects.all()

    def get_queryset(self):
        return PublishedRecord.objects.filter(is_published=True).order_by(
            "-published_at", "id"
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        records = list(queryset)
        sites = AdminConsoleInterface.public_site_details(
            [record.site for record in records]
        )
        results = []
        for record in records:
            site = sites.get(record.site)
            if site is None:
                continue
            results.append(
                {
                    "id": record.pk,
                    "domain": site["domain"],
                    "company_name": site["company_name"],
                    "plan_type": record.plan_type,
                    "values": record.values,
                    "published_at": (
                        record.published_at.isoformat()
                        if record.published_at
                        else None
                    ),
                }
            )
        return Response({"plans": results})


class RecentCompaniesViewSet(GenericViewSet):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="companies/recent")
    def recent(self, request):
        now = timezone.localtime()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        companies = AdminConsoleInterface.public_recent_companies(month_start)
        return Response(
            {
                "companies": [
                    {
                        "domain": company["domain"],
                        "company_name": company["company_name"],
                        "created_at": company["created_at"].isoformat(),
                    }
                    for company in companies
                ]
            }
        )
