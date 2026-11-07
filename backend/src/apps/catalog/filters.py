import math

import django_filters
from django.db.models import Q

from apps.pipeline.interfaces import PipelineInterface
from apps.catalog.models import PublishedRecord
from apps.pipeline.plan_schema import PLAN_SCHEMA, SchemaField


# Sensible defaults used when a field carries a `unit_family` but the caller
# doesn't specify a unit explicitly. This keeps the generated filter usable
# without the frontend having to send `storage_unit=GB` etc. every time.
UNIT_DEFAULTS: dict[str, str] = {
    "data_size": "GB",
    "rate": "per_second",
    "currency": "USD",
}

RESOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "ram": ("ram_amount", "ram"),
    "cpu": ("vcpu_cores", "cpu_cores", "cpu"),
    "disk": ("storage_amount", "disk_amount", "disk"),
    "traffic": ("traffic_amount", "bandwidth_amount", "traffic", "bandwidth"),
}

RESOURCE_UNITS: dict[str, str] = {
    "ram": "GB",
    "cpu": "core",
    "disk": "GB",
    "traffic": "GB",
}

RESOURCE_UNIT_ALIASES: dict[str, tuple[str, ...]] = {
    "ram": ("ram_unit",),
    "cpu": (),
    "disk": ("storage_unit", "disk_unit"),
    "traffic": ("traffic_unit", "bandwidth_unit"),
}

DATA_SIZE_TO_GB: dict[str, float] = {
    "B": 1 / (1024**3),
    "KB": 1 / (1024**2),
    "MB": 1 / 1024,
    "GB": 1,
    "TB": 1024,
    "PB": 1024**2,
}

PLAN_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "host": ("hosting", "wordpress"),
    "virtual_server": ("virtual_server", "vps"),
    "dedicated_server": ("dedicated_server", "dedicated"),
    "cdn": ("cdn",),
}


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def normalize_resource_value(resource: str, values: dict) -> float | None:
    """Return one plan's resource value in its canonical filter unit."""
    if not isinstance(values, dict):
        return None
    for alias in RESOURCE_ALIASES[resource]:
        amount = _number(values.get(alias))
        if amount is None:
            continue
        if resource == "cpu":
            return amount
        unit = None
        for unit_alias in RESOURCE_UNIT_ALIASES[resource]:
            candidate = values.get(unit_alias)
            if isinstance(candidate, str) and candidate.strip():
                unit = candidate.strip().upper()
                break
        factor = DATA_SIZE_TO_GB.get(unit or "GB", 1)
        return round(amount * factor, 6)
    return None


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _json_values(values: list[str]) -> list:
    parsed: list = []
    for value in values:
        if value not in parsed:
            parsed.append(value)
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number not in parsed:
            parsed.append(number)
    return parsed


def _filter_for_field(schema_field: SchemaField):
    """Return the django-filter class (and lookup) for one schema field.

    - number  -> NumberFilter
    - enum    -> ChoiceFilter
    - text    -> CharFilter
    """
    if schema_field.kind == "number":
        return django_filters.NumberFilter
    if schema_field.kind == "enum" and schema_field.values:
        return django_filters.ChoiceFilter
    return django_filters.CharFilter


def _build_dynamic_filter_fields(plan_type: str) -> dict:
    """Translate a single PlanSchema into a `declared_filters` dict.

    Rules:
      * skip the pseudo-field ``other`` (never a real extracted column),
      * if a field has a ``unit_family``, register a matching ``<key>_unit``
        companion filter defaulting to ``UNIT_DEFAULTS[unit_family]``.
    """
    plan = PLAN_SCHEMA.get(plan_type)
    if plan is None:
        return {}

    declared = {}
    for schema_field in plan.fields:
        # 1. skip the `other` field — it's not a real column.
        if schema_field.key == "other":
            continue

        # 2. pick the right filter class based on the schema kind.
        filter_cls = _filter_for_field(schema_field)

        # 3. build kwargs, using values for enums.
        kwargs = {}
        if schema_field.kind == "enum" and schema_field.values:
            kwargs["choices"] = [(v, v) for v in schema_field.values]
        # numbers may be fractional in some plans; keep it permissive.
        if schema_field.kind == "number":
            kwargs["method"] = _make_number_method(schema_field.key)

        declared[schema_field.key] = filter_cls(**kwargs)

        # 4. attach a default unit filter when the field has a unit family.
        if schema_field.unit_family:
            declared[f"{schema_field.key}_unit"] = django_filters.CharFilter(
                method=_make_unit_method(schema_field.key, schema_field.unit_family),
                label=f"{schema_field.label} unit",
                # NOTE: filters don't hold defaults themselves; we apply the
                # default inside the method so the user can omit it in the URL.
            )

    return declared


def _make_number_method(key: str):
    def method(self, queryset, name, value):
        # Only apply the filter if a value was sent. We compare against the
        # denormalized `values` JSON on PublishedRecord.
        if value in (None, ""):
            return queryset
        return queryset.filter(**{f"values__{key}": value})
    return method


def _make_unit_method(key: str, unit_family: str):
    default_unit = UNIT_DEFAULTS.get(unit_family)

    def method(self, queryset, name, value):
        unit = value or default_unit
        if unit is None:
            return queryset
        return queryset.filter(**{f"values__{key}_unit": unit})
    return method


class PublishedPlanFilter(django_filters.FilterSet):

    domain = django_filters.CharFilter(method="filter_domain")
    q = django_filters.CharFilter(method="filter_search")
    type = django_filters.CharFilter(method="filter_type")
    sort = django_filters.ChoiceFilter(
        choices=(
            ("price", "price"),
            ("expensive", "expensive"),
            ("relevance", "relevance"),
        ),
        method="filter_sort",
    )
    providers = django_filters.CharFilter(method="filter_providers")
    os = django_filters.CharFilter(method="filter_os")
    location = django_filters.CharFilter(method="filter_location")
    ram = django_filters.CharFilter(method="filter_resource")
    cpu = django_filters.CharFilter(method="filter_resource")
    disk = django_filters.CharFilter(method="filter_resource")
    traffic = django_filters.CharFilter(method="filter_resource")

    class Meta:
        model = PublishedRecord
        fields = ["type"]

    def __init__(self, *args, plan_type: str | None = None, **kwargs):
        """Attach the schema-derived fields for the requested plan type.

        ``plan_type`` is normally derived from the request (e.g. the URL kwarg
        or ``data["type"]``); callers can also pass it explicitly.
        """
        super().__init__(*args, **kwargs)
        if plan_type is None:
            plan_type = self.data.get("type")
        if plan_type:
            for key, flt in _build_dynamic_filter_fields(plan_type).items():
                self.filters[key] = flt

    def _resolve_sites(self, queryset):
        return PipelineInterface.public_site_details(
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

    def filter_type(self, queryset, name, value):
        return queryset.filter(
            plan_type__in=PLAN_TYPE_ALIASES.get(value, (value,))
        )

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

    def filter_providers(self, queryset, name, value):
        wanted = {item.casefold() for item in _csv(value)}
        if not wanted:
            return queryset
        site_ids = [
            site.pk
            for site in PipelineInterface.all_sites()
            if site.domain.casefold() in wanted
            or site.company.company_name.casefold() in wanted
        ]
        return queryset.filter(site__in=site_ids)

    def filter_os(self, queryset, name, value):
        wanted = _csv(value)
        if not wanted:
            return queryset
        query = Q()
        for key in ("os", "operating_system"):
            for item in wanted:
                query |= Q(**{f"values__{key}__iexact": item})
        return queryset.filter(query)

    def filter_location(self, queryset, name, value):
        wanted = _csv(value)
        if not wanted:
            return queryset
        query = Q()
        for key in ("location", "datacenter_location"):
            for item in wanted:
                query |= Q(**{f"values__{key}__iexact": item})
        return queryset.filter(query)

    def filter_resource(self, queryset, name, value):
        values = _json_values(_csv(value))
        if not values:
            return queryset
        requested = [float(item) for item in values]
        matching_ids = [
            record.pk
            for record in queryset
            if (normalized := normalize_resource_value(name, record.values)) is not None
            and any(
                math.isclose(normalized, wanted, rel_tol=1e-6, abs_tol=1e-6)
                for wanted in requested
            )
        ]
        return queryset.filter(pk__in=matching_ids)

    def filter_sort(self, queryset, name, value):
        if value == "price":
            return queryset.order_by("values__price_amount", "id")
        if value == "expensive":
            return queryset.order_by("-values__price_amount", "id")
        return queryset
