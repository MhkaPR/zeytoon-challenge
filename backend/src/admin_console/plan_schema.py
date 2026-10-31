"""The single, code-defined plan schema (FR-027).

The schema describes a **list of plans** of one plan type (for example a hosting plans
page yields several plans). :class:`PlanSchema` is an immutable dataclass over the plan
item's fields; :meth:`PlanSchema.list_model` builds the Pydantic model the LLM output is
validated against — ``{"plans": [ {field: value, ...}, ... ]}``.

The LLM extracts data against this schema: data only, no selectors and no formulas
(FR-028). The schema is edited by hand and is never user-editable. Subclass
``SchemaField``/``PlanSchema`` or extend :data:`PLAN_SCHEMA` to add plan types.
"""

from dataclasses import dataclass, field
from typing import Optional

from pydantic import create_model


@dataclass(frozen=True)
class SchemaField:
    """One field of a single plan item."""

    key: str
    label: str
    kind: str  # text | number | enum
    required: bool = True
    unit_family: str | None = None
    values: tuple[str, ...] = ()

    @property
    def python_type(self):
        return float if self.kind == "number" else str


@dataclass(frozen=True)
class PlanSchema:
    """Describes a **list of plans** of one plan type.

    ``fields`` describes one plan item; the list is the unit of extraction.
    """

    key: str
    label: str
    fields: tuple[SchemaField, ...] = field(default_factory=tuple)

    def field_map(self):
        return {f.key: f for f in self.fields}

    def required_keys(self):
        return {f.key for f in self.fields if f.required}

    def item_model(self, name=None):
        """A Pydantic model for one plan item of this type."""
        definitions = {}
        for schema_field in self.fields:
            annotation = schema_field.python_type
            if schema_field.required:
                definitions[schema_field.key] = (annotation, ...)
            else:
                definitions[schema_field.key] = (
                    Optional[annotation],
                    None,
                )
        return create_model(name or f"PlanItem_{self.key}", **definitions)

    def list_model(self, name=None):
        """The Pydantic model for the extraction output: a list of plan items (FR-026)."""
        item = self.item_model()
        return create_model(
            name or f"PlanList_{self.key}",
            plans=(list[item], ...),
        )


PLAN_SCHEMA: dict[str, PlanSchema] = {
    "hosting": PlanSchema(
        key="hosting",
        label="Hosting",
        fields=(
            SchemaField("plan_name", "Plan name", "text"),
            SchemaField(
                "storage_amount", "Storage amount", "number", required=False,
                unit_family="data_size",
            ),
            SchemaField(
                "storage_unit", "Storage unit", "enum", required=False,
                values=("GB", "TB"),
            ),
            SchemaField(
                "ram_amount", "RAM amount", "number", required=False,
                unit_family="data_size",
            ),
            SchemaField("cpu_cores", "CPU cores", "number", required=False),
            SchemaField(
                "bandwidth_amount", "Bandwidth amount", "number", required=False,
                unit_family="data_size",
            ),
            SchemaField("price_amount", "Price amount", "number", unit_family="currency"),
            SchemaField(
                "billing_period", "Billing period", "enum", required=False,
                values=("monthly", "yearly"),
            ),
        ),
    ),
    "cdn": PlanSchema(
        key="cdn",
        label="CDN",
        fields=(
            SchemaField("plan_name", "Plan name", "text"),
            SchemaField("traffic_amount", "Traffic amount", "number", required=False,
                        unit_family="data_size"),
            SchemaField("request_rate", "Request rate", "number", required=False,
                        unit_family="rate"),
            SchemaField("price_amount", "Price amount", "number", unit_family="currency"),
        ),
    ),
    "virtual_server": PlanSchema(
        key="virtual_server",
        label="Virtual server",
        fields=(
            SchemaField("plan_name", "Plan name", "text"),
            SchemaField("vcpu_cores", "vCPU cores", "number", required=False),
            SchemaField(
                "ram_amount", "RAM amount", "number", required=False,
                unit_family="data_size",
            ),
            SchemaField(
                "disk_amount", "Disk amount", "number", required=False,
                unit_family="data_size",
            ),
            SchemaField("os", "OS", "enum", required=False),
            SchemaField("price_amount", "Price amount", "number", unit_family="currency"),
        ),
    ),
}


def get_plan_type(key):
    return PLAN_SCHEMA.get(key)


def schema_for(plan_type):
    return PLAN_SCHEMA.get(plan_type)


def required_keys(plan_type):
    plan = PLAN_SCHEMA.get(plan_type)
    return plan.required_keys() if plan else set()


def required_fields(plan_type):
    return required_keys(plan_type)


def all_field_keys(plan_type):
    plan = PLAN_SCHEMA.get(plan_type)
    return set(plan.field_map()) if plan else set()


def list_model(plan_type):
    """The Pydantic list-of-plans model for a plan type (FR-026)."""
    plan = PLAN_SCHEMA.get(plan_type)
    return plan.list_model() if plan else None
