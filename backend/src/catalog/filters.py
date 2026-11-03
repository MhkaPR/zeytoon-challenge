import django_filters

from admin_console.interfaces import AdminConsoleInterface
from catalog.models import PublishedRecord


class PublishedPlanFilter(django_filters.FilterSet):

    domain = django_filters.CharFilter(method="filter_domain")
    q = django_filters.CharFilter(method="filter_search")
    type = django_filters.CharFilter(field_name="plan_type")

    class Meta:
        model = PublishedRecord
        fields = ["type"]

    def _resolve_sites(self, queryset):
        return AdminConsoleInterface.public_site_details(
            [record.site for record in queryset]
        )

    def filter_domain(self, queryset, name, value):
        needle = value.casefold()
        sites = self._resolve_sites(queryset)
        matching_ids = [
            record.pk
            for record in queryset
            if (site := sites.get(record.site)) is not None
            and site["domain"].casefold() == needle
        ]
        return queryset.filter(pk__in=matching_ids)

    def filter_search(self, queryset, name, value):
        needle = value.casefold()
        sites = self._resolve_sites(queryset)
        matching_ids = [
            record.pk
            for record in queryset
            if (site := sites.get(record.site)) is not None
            and needle in f"{site['company_name']} {record.values}".casefold()
        ]
        return queryset.filter(pk__in=matching_ids)