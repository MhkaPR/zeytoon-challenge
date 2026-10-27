"""The single, code-defined plan schema (FR-027).

Recipes bind to a field ``key``; ``required`` fields gate recipe completeness (FR-030);
``unit_family`` feeds the cleaning engine (FR-032); ``enum`` ``values`` constrain
category normalization. This schema is never user-editable.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SchemaField:
    key: str
    label: str
    kind: str  # text | number | enum
    required: bool = True
    unit_family: str | None = None
    values: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanType:
    key: str
    label: str
    fields: tuple[SchemaField, ...] = field(default_factory=tuple)

    def field_map(self):
        return {f.key: f for f in self.fields}

    def required_keys(self):
        return {f.key for f in self.fields if f.required}


PLAN_SCHEMA: dict[str, PlanType] = {
    "hosting": PlanType(
        key="hosting",
        label="Hosting",
        fields=(
            SchemaField("plan_name", "Plan name", "text"),
            SchemaField("storage_amount", "Storage amount", "number", unit_family="data_size"),
            SchemaField("storage_unit", "Storage unit", "enum", values=("GB", "TB")),
            SchemaField("ram_amount", "RAM amount", "number", unit_family="data_size"),
            SchemaField("cpu_cores", "CPU cores", "number"),
            SchemaField(
                "bandwidth_amount", "Bandwidth amount", "number", unit_family="data_size"
            ),
            SchemaField(
                "price_amount", "Price amount", "number", unit_family="currency"
            ),
            SchemaField(
                "billing_period",
                "Billing period",
                "enum",
                values=("monthly", "yearly"),
            ),
        ),
    ),
    "cdn": PlanType(
        key="cdn",
        label="CDN",
        fields=(
            SchemaField("plan_name", "Plan name", "text"),
            SchemaField(
                "traffic_amount", "Traffic amount", "number", unit_family="data_size"
            ),
            SchemaField(
                "request_rate",
                "Request rate",
                "number",
                required=False,
                unit_family="rate",
            ),
            SchemaField(
                "price_amount", "Price amount", "number", unit_family="currency"
            ),
        ),
    ),
    "virtual_server": PlanType(
        key="virtual_server",
        label="Virtual server",
        fields=(
            SchemaField("plan_name", "Plan name", "text"),
            SchemaField("vcpu_cores", "vCPU cores", "number"),
            SchemaField("ram_amount", "RAM amount", "number", unit_family="data_size"),
            SchemaField(
                "disk_amount", "Disk amount", "number", unit_family="data_size"
            ),
            SchemaField("os", "OS", "enum", required=False),
            SchemaField(
                "price_amount", "Price amount", "number", unit_family="currency"
            ),
        ),
    ),
}


def get_plan_type(key):
    return PLAN_SCHEMA.get(key)


def required_keys(plan_type):
    plan = PLAN_SCHEMA.get(plan_type)
    return plan.required_keys() if plan else set()


def all_field_keys(plan_type):
    plan = PLAN_SCHEMA.get(plan_type)
    return set(plan.field_map()) if plan else set()
