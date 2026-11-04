import django_filters

from apps.admin_console.interfaces import AdminConsoleInterface
from apps.catalog.models import PublishedRecord
from apps.admin_console.plan_schema import PLAN_SCHEMA, SchemaField


# Sensible defaults used when a field carries a `unit_family` but the caller
# doesn't specify a unit explicitly. This keeps the generated filter usable
# without the frontend having to send `storage_unit=GB` etc. every time.
UNIT_DEFAULTS: dict[str, str] = {
    "data_size": "GB",
    "rate": "per_second",
    "currency": "USD",
}


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
    type = django_filters.CharFilter(field_name="plan_type")

    class Meta:
        model = PublishedRecord
        fields = ["type"]

    def __init__(self, *args, plan_type: str | None = None, **kwargs):
        """Attach the schema-derived fields for the requested plan type.

        ``plan_type`` is normally derived from the request (e.g. the URL kwarg
        or ``data["type"]``); callers can also pass it explicitly.
        """
        super().__init__(*args, **kwargs)
        if plan_type:
            for key, flt in _build_dynamic_filter_fields(plan_type).items():
                self.filters[key] = flt

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