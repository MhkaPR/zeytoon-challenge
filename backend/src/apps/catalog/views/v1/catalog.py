"""Read-only public API for currently published plans."""

from django.utils import timezone
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.pipeline.interfaces import PipelineInterface
from apps.catalog.filters import RESOURCE_ALIASES, PublishedPlanFilter
from apps.catalog.models import PublishedRecord
from apps.catalog.serializers.v1.catalog import (
    PublicCompanySerializer,
    PublicPlanSerializer,
)
from apps.core.site_config import public_site_config
from apps.utils.views import EnvelopeListViewSet


class SiteConfigViewSet(GenericViewSet):
    """Public runtime configuration consumed by the frontend SPA."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="site-config")
    def site_config(self, request):
        return Response(public_site_config())


class PublishedCompaniesViewSet(EnvelopeListViewSet):
    authentication_classes = []
    permission_classes = []
    serializer_class = PublicCompanySerializer

    def get_queryset(self):
        queryset = (
            PublishedRecord.objects.filter(is_published=True)
            .values("site")
            .annotate(plan_count=Count("id"))
            .order_by("-plan_count", "site")
        )
        search = self.request.query_params.get("q", "").strip()
        if search:
            needle = search.casefold()
            site_ids = [
                site.pk
                for site in PipelineInterface.all_sites()
                if needle in site.domain.casefold()
                or needle in site.company.company_name.casefold()
            ]
            queryset = queryset.filter(site__in=site_ids)
        return queryset

    def serialize_page(self, rows):
        rows = list(rows)
        sites = PipelineInterface.public_site_details(
            [row["site"] for row in rows]
        )
        data = [
            {
                "domain": site["domain"],
                "company_name": site["company_name"],
                "plan_count": row["plan_count"],
            }
            for row in rows
            if (site := sites.get(row["site"])) is not None
        ]
        return PublicCompanySerializer(data, many=True).data


class PublishedPlansViewSet(EnvelopeListViewSet):
    authentication_classes = []
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = PublishedPlanFilter
    serializer_class = PublicPlanSerializer
    queryset = PublishedRecord.objects.all()

    def get_queryset(self):
        return PublishedRecord.objects.filter(is_published=True).order_by(
            "-published_at", "id"
        )

    def serialize_page(self, records):
        records = list(records)
        sites = PipelineInterface.public_site_details(
            [record.site for record in records]
        )
        links = PipelineInterface.public_link_urls(
            [record.link for record in records]
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
                    "url": links.get(record.link),
                    "published_at": (
                        record.published_at.isoformat()
                        if record.published_at
                        else None
                    ),
                }
            )
        return PublicPlanSerializer(results, many=True).data

    def get_page_extra(self):
        plan_type = self.request.query_params.get("type")
        facet_filterset = self.filterset_class(
            data={"type": plan_type} if plan_type else {},
            queryset=self.get_queryset(),
        )
        return {"facets": self._facets(facet_filterset.qs)}

    @staticmethod
    def _facets(queryset):
        records = list(queryset.values("site", "values"))
        sites = PipelineInterface.public_site_details(
            [record["site"] for record in records]
        )
        companies = sorted(
            {
                site["company_name"]
                for record in records
                if (site := sites.get(record["site"])) is not None
            },
            key=str.casefold,
        )
        operating_systems: set[str] = set()
        locations: set[str] = set()
        resources: dict[str, set[float]] = {
            key: set() for key in RESOURCE_ALIASES
        }
        for record in records:
            values = record["values"] or {}
            for key in ("os", "operating_system"):
                if values.get(key):
                    operating_systems.add(str(values[key]))
            for key in ("location", "datacenter_location"):
                if values.get(key):
                    locations.add(str(values[key]))
            for resource, aliases in RESOURCE_ALIASES.items():
                for alias in aliases:
                    value = values.get(alias)
                    if isinstance(value, (int, float)) and value > 0:
                        resources[resource].add(float(value))
                        break
        return {
            "companies": companies,
            "operating_systems": sorted(operating_systems, key=str.casefold),
            "locations": sorted(locations, key=str.casefold),
            "resources": {
                key: sorted(values) for key, values in resources.items()
            },
        }


class RecentCompaniesViewSet(GenericViewSet):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="companies/recent")
    def recent(self, request):
        now = timezone.localtime()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        companies = PipelineInterface.public_recent_companies(month_start)
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
