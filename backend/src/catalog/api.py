"""Read-only public API for currently published plans."""

from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from admin_console.interfaces import AdminConsoleInterface
from catalog.filters import PublishedPlanFilter
from catalog.models import PublishedRecord
from core.site_config import public_site_config


class SiteConfigView(APIView):
    """Public runtime configuration consumed by the frontend SPA."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(public_site_config())


class PublishedPlansView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        queryset = PublishedRecord.objects.filter(is_published=True).order_by(
            "-published_at", "id"
        )
        queryset = PublishedPlanFilter(request.query_params, queryset=queryset).qs

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


class RecentCompaniesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        now = timezone.localtime()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        companies = AdminConsoleInterface.public_recent_companies(month_start)
        return Response({
            "companies": [
                {
                    "domain": company["domain"],
                    "company_name": company["company_name"],
                    "created_at": company["created_at"].isoformat(),
                }
                for company in companies
            ]
        })