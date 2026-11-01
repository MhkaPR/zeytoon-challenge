"""The single, code-defined plan schema (FR-027) — pure Pydantic implementation.

Design rules enforced by this module:

- Every plan type is a standalone ``BaseModel``. There is no meta-schema, no
  dataclass, and no intermediate registry of field descriptors.
- Every model uses ``extra="forbid"``. This is the enforcement mechanism: any
  key the LLM emits that is not declared on the model is rejected, and the
  retry layer (pydantic-ai, Instructor, …) re-prompts the model with the
  validation error. Unmapped source-table data must be placed in ``other``.
- ``other`` is modelled as ``list[OtherEntry]`` rather than ``dict[str, Any]``
  because OpenAI strict structured outputs reject free-form
  ``additionalProperties``; a list of typed ``{key, value}`` objects is
  strict-mode safe and round-trips cleanly.
- The helper functions keep the exact public names and behavior of the
  original module, re-implemented against :data:`PLAN_MODELS`.

FR-028: the LLM extracts data only — no selectors, no formulas.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model


# ============================================================
# Support types
# ============================================================

class OtherEntry(BaseModel):
    """One key/value pair for data that did not map to any schema field."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(
        description="Meaningful snake_case key derived from the source table header",
    )
    value: str = Field(
        description="Value serialized as text (numbers, booleans, etc. as strings)",
    )


# Reusable literal types (canonical values only — aliases live in prompts/normalizer)
DataUnit = Literal["MB", "GB", "TB"]
BillingPeriod = Literal["monthly", "quarterly", "semiannual", "yearly"]
DiskType = Literal["hdd", "ssd", "nvme", "sas"]
VirtualizationType = Literal["kvm", "openvz", "vmware", "hyperv", "xen"]
ControlPanel = Literal["cpanel", "directadmin", "plesk", "website_panel", "other"]
Currency = Literal["toman", "rial"]


# ============================================================
# Base classes
# ============================================================

class _BasePlanItem(BaseModel):
    """Shared fields for every plan item.

    ``extra="forbid"`` is the force mechanism: undeclared fields are rejected,
    so the LLM has no escape hatch other than ``other``.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    plan_name: str = Field(description="Plan name exactly as shown in the table")
    other: list[OtherEntry] = Field(
        default_factory=list,
        description=(
            "Data from the source table that did not map to any schema field. "
            "Use meaningful snake_case keys; values are strings."
        ),
    )


class _PricedPlanItem(_BasePlanItem):
    """Adds one normalized price to the base item."""

    price_amount: int | None = Field(
        None,
        description=(
            "Final price in Toman (integer). Rial values must be divided by 10. "
            "Note: '1000 million Toman' means 1,000,000,000 Toman."
        ),
        json_schema_extra={"family": "currency", "unit": "toman"},
    )
    price_raw: str | None = Field(
        None,
        description="Raw price text as it appeared in the table (for audit)",
    )
    currency: Currency = Field("toman", description="Currency after normalization")
    billing_period: BillingPeriod | None = Field(
        None, description="Billing cycle the price refers to"
    )


# ============================================================
# Domain models
# ============================================================

class HostingPlan(_PricedPlanItem):
    """Shared hosting plan (cPanel / DirectAdmin / Plesk)."""

    storage_amount: float | None = Field(
        None, description="Disk space amount",
        json_schema_extra={"family": "data_size"},
    )
    storage_unit: DataUnit | None = Field(None, description="Disk space unit")
    ram_amount: float | None = Field(
        None, description="RAM amount",
        json_schema_extra={"family": "data_size"},
    )
    ram_unit: DataUnit | None = Field(None, description="RAM unit")
    cpu_cores: int | None = Field(None, description="Number of CPU cores")
    bandwidth_amount: float | None = Field(
        None, description="Monthly bandwidth amount",
        json_schema_extra={"family": "data_size"},
    )


class ResellerPlan(_PricedPlanItem):
    """Reseller hosting plan."""

    account_count: int | None = Field(
        None, description="Maximum number of cPanel accounts",
    )
    storage_amount: float | None = None
    storage_unit: DataUnit | None = None
    bandwidth_amount: float | None = None
    bandwidth_unit: DataUnit | None = None
    control_panel: ControlPanel | None = None
    whm_included: bool | None = Field(
        None, description="Whether WHM is included",
    )


class VirtualServerPlan(_PricedPlanItem):
    """Virtual server (VPS) plan."""

    vcpu_cores: int | None = Field(None, description="Number of vCPU cores")
    ram_amount: float | None = None
    ram_unit: DataUnit | None = None
    disk_amount: float | None = None
    disk_unit: DataUnit | None = None
    disk_type: DiskType | None = None
    os: str | None = Field(None, description="Operating system")
    location: str | None = None
    virtualization: VirtualizationType | None = None
    managed: bool | None = Field(
        None, description="Whether the server is fully managed",
    )


class DedicatedServerPlan(_PricedPlanItem):
    """Dedicated server plan."""

    cpu_model: str | None = None
    cpu_cores: int | None = None
    cpu_threads: int | None = None
    ram_amount: float | None = None
    ram_unit: DataUnit | None = None
    disk_amount: float | None = None
    disk_unit: DataUnit | None = None
    disk_type: DiskType | None = None
    bandwidth_amount: float | None = None
    bandwidth_unit: DataUnit | None = None
    port_speed_mbps: float | None = Field(
        None, description="Network port speed in Mbps",
    )
    ipv4_count: int | None = None
    ipv6_count: int | None = None
    location: str | None = None
    datacenter: str | None = None
    os_supported: str | None = None
    managed: bool | None = None


class CloudServerPlan(_PricedPlanItem):
    """Cloud server plan."""

    vcpu_cores: int | None = None
    ram_amount: float | None = None
    ram_unit: DataUnit | None = None
    disk_amount: float | None = None
    disk_unit: DataUnit | None = None
    disk_type: DiskType | None = None
    hourly_price_toman: int | None = Field(
        None, description="Hourly price in Toman, if billed hourly",
    )
    location: str | None = None
    auto_scaling: bool | None = None


class DomainPricing(_BasePlanItem):
    """One row of a TLD pricing table."""

    tld: str | None = Field(None, description="Canonical TLD, e.g. '.com' or '.ir'")
    register_price: int | None = Field(
        None, description="Registration price in Toman",
        json_schema_extra={"family": "currency", "unit": "toman"},
    )
    register_price_raw: str | None = None
    renewal_price: int | None = Field(
        None, description="Renewal price in Toman",
        json_schema_extra={"family": "currency", "unit": "toman"},
    )
    renewal_price_raw: str | None = None
    transfer_price: int | None = Field(
        None, description="Transfer price in Toman",
        json_schema_extra={"family": "currency", "unit": "toman"},
    )
    transfer_price_raw: str | None = None
    restore_price: int | None = Field(
        None, description="Restore-after-expiry price in Toman",
    )
    min_years: int | None = None
    max_years: int | None = None
    whois_privacy_included: bool | None = None
    currency: Currency = "toman"


class SupportPlan(_PricedPlanItem):
    """Support tier / SLA plan."""

    sla_uptime_pct: float | None = Field(None, ge=0, le=100)
    response_time_hours: float | None = None
    resolution_time_hours: float | None = None
    channels: str | None = Field(
        None,
        description="Comma-separated list of channels, e.g. 'phone,email,chat'",
    )
    hours_of_operation: str | None = Field(
        None, description="e.g. '24/7' or 'business hours'",
    )


class CDNPlan(_PricedPlanItem):
    """CDN plan."""

    traffic_amount: float | None = Field(
        None, json_schema_extra={"family": "data_size"},
    )
    traffic_unit: DataUnit | None = None
    request_rate: float | None = Field(
        None, description="Requests per second",
        json_schema_extra={"family": "rate"},
    )
    edge_locations_count: int | None = None
    ssl_included: bool | None = None


class SSLPlan(_PricedPlanItem):
    """SSL certificate plan."""

    validation_type: Literal["dv", "ov", "ev"] | None = None
    scope: Literal["single", "wildcard", "multi_domain"] | None = None
    domains_covered: int | None = None
    warranty_usd: int | None = None
    validity_days: int | None = None


# ============================================================
# Registry — the single source of truth for plan types
# ============================================================

PLAN_MODELS: dict[str, type[_BasePlanItem]] = {
    "hosting": HostingPlan,
    "reseller": ResellerPlan,
    "virtual_server": VirtualServerPlan,
    "dedicated_server": DedicatedServerPlan,
    "cloud_server": CloudServerPlan,
    "domain": DomainPricing,
    "support": SupportPlan,
    "cdn": CDNPlan,
    "ssl": SSLPlan,
}


# ============================================================
# Public helpers — preserved names, re-implemented for pure Pydantic
# ============================================================

def get_plan_type(key: str) -> type[_BasePlanItem] | None:
    return PLAN_MODELS.get(key)


def schema_for(plan_type: str) -> type[_BasePlanItem] | None:
    return PLAN_MODELS.get(plan_type)


def required_keys(plan_type: str) -> set[str]:
    cls = PLAN_MODELS.get(plan_type)
    if cls is None:
        return set()
    return {
        name
        for name, field_info in cls.model_fields.items()
        if field_info.is_required()
    }


def required_fields(plan_type: str) -> set[str]:
    return required_keys(plan_type)


def all_field_keys(plan_type: str) -> set[str]:
    cls = PLAN_MODELS.get(plan_type)
    return set(cls.model_fields) if cls else set()


def list_model(plan_type: str):
    """The Pydantic list-of-plans model for a plan type (FR-026)."""
    cls = PLAN_MODELS.get(plan_type)
    if cls is None:
        return None
    return create_model(
        f"PlanList_{cls.__name__}",
        __config__=ConfigDict(extra="forbid"),
        plans=(list[cls], ...),
    )


def extraction_model(plan_type: str):
    """Strict response shape returned by plan extraction."""
    cls = PLAN_MODELS.get(plan_type)
    if cls is None:
        return None
    record = create_model(
        f"PlanRecord_{cls.__name__}",
        __config__=ConfigDict(extra="forbid"),
        values=(cls, ...),
        confidence=(float | None, ...),
    )
    return create_model(
        f"PlanExtraction_{cls.__name__}",
        __config__=ConfigDict(extra="forbid"),
        plans=(list[record], ...),
    )