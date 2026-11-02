"""OpenAI-compatible LLM client and the admin-owned token budget (FR-023, FR-026, FR-047).

Provider is OpenAI-compatible: the base URL and key come from the environment (Iran uses
a gateway). Every call is gated by the token budget; when it is exhausted no call is
made, no partial row is written, and the caller parks the link in
``awaiting_llm_budget`` (FR-048).

Both behaviors live in small classes — :class:`LlmBudget` and :class:`LlmClient` — so a
developer can subclass them or inject fakes in tests. The module-level defaults
(:data:`default_budget`, :data:`default_client`) keep the functional API convenient.
"""

import json
import logging
import uuid

import httpx
from django.conf import settings
from django.utils import timezone
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    field_validator,
)

from admin_console import plan_schema
from admin_console.models import Link, LlmCostLedger

PROMPT_VERSION = "v1"
logger = logging.getLogger(__name__)


def _strict_json_schema(model):
    """Convert a Pydantic schema to OpenAI Structured Outputs strict form."""
    schema = model.model_json_schema()

    def normalize(node):
        if isinstance(node, list):
            return [normalize(item) for item in node]
        if not isinstance(node, dict):
            return node
        node = {key: normalize(value) for key, value in node.items()}
        if node.get("type") == "object" or "properties" in node:
            props = node.get("properties", {})
            node["required"] = list(props)
            node["additionalProperties"] = False
        return node

    return normalize(schema)


class LlmError(Exception):
    """The provider was reachable but returned an unusable response."""


class NoPlanRecordsError(LlmError):
    """Extraction ran successfully but no plan met the quality requirements."""


class LlmBudgetExhausted(Exception):
    """The token budget is exhausted, so no LLM call may be made (FR-048)."""


def _sanitize_plan_values(raw_values, plan_type):
    """Coerce one record's fields onto its plan schema without discarding data.

    Unknown keys are preserved in ``values.other`` and mismatched types are coerced
    or dropped, mirroring the standalone extraction path. Returns the cleaned dict,
    or ``None`` when the record is unusable (no ``plan_name`` or not a mapping).
    """
    if not isinstance(raw_values, dict):
        return None
    values = dict(raw_values)
    fields = plan_schema.schema_for(plan_type).field_map()
    allowed_fields = set(fields)
    other = values.get("other", [])
    if not isinstance(other, list):
        other = []
    else:
        other = [
            entry
            for entry in other
            if isinstance(entry, dict)
            and entry.get("key") not in (None, "")
            and entry.get("value") not in (None, "")
        ]
    for key in list(values):
        if key not in allowed_fields and key != "other":
            value = values.pop(key)
            if value not in (None, ""):
                other.append({"key": str(key), "value": str(value)})
    values["other"] = other
    for key, value in list(values.items()):
        if key == "other" or value is None:
            continue
        field = fields[key]
        try:
            if field.kind == "number":
                values[key] = float(value)
            elif field.kind == "enum" and field.values and value not in field.values:
                values.pop(key)
            elif field.kind == "text" and not isinstance(value, str):
                values[key] = str(value)
        except TypeError, ValueError:
            values.pop(key)
    if not values.get("plan_name"):
        return None
    return values


class PlanRecordOut(BaseModel):
    values: dict
    confidence: float | None = None


class CombinedTableOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_index: int
    is_correct: bool
    plan_type: str | None = None
    classification_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("classification_confidence", "confidence"),
    )
    plans: list[PlanRecordOut] | None = None

    @field_validator("classification_confidence", mode="before")
    @classmethod
    def normalize_classification_confidence(cls, value):
        """Accept common qualitative confidence labels from imperfect gateways."""
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower().replace("_", " ").replace("-", " ")
            qualitative = {
                "very low": 0.2,
                "low": 0.35,
                "medium": 0.6,
                "moderate": 0.6,
                "high": 0.85,
                "very high": 0.95,
            }
            if normalized in qualitative:
                return qualitative[normalized]
            try:
                return float(normalized)
            except ValueError:
                return 0.0
        return value


class CombinedTablesOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tables: list[CombinedTableOut]


class ClassificationOut(BaseModel):
    table_index: int
    is_correct: bool
    plan_type: str | None = None
    confidence: float = 0.0


class LlmBudget:
    """Token budget + spend ledger (FR-047..FR-050)."""

    def __init__(self, scope="global", period="monthly"):
        self.scope = scope
        self.period = period

    @staticmethod
    def _period_start(period, now=None):
        now = now or timezone.now()
        if period == LlmCostLedger.Period.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == LlmCostLedger.Period.MONTHLY:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None

    def current_budget(self, scope=None, period=None):
        scope, period = scope or self.scope, period or self.period
        row = (
            LlmCostLedger.objects.filter(
                scope=scope, period=period, token_budget__isnull=False
            )
            .order_by("-created_at")
            .first()
        )
        return row.token_budget if row else None

    def tokens_used(self, scope=None, period=None):
        scope, period = scope or self.scope, period or self.period
        qs = LlmCostLedger.objects.filter(scope=scope, period=period)
        start = self._period_start(period)
        if start is not None:
            qs = qs.filter(created_at__gte=start)
        return sum(row.tokens_used for row in qs)

    def allows(self, scope=None, period=None):
        budget = self.current_budget(scope, period)
        if budget is None:
            return True
        return self.tokens_used(scope, period) < budget

    def set_budget(self, amount, period=None, scope=None, actor=None):
        return LlmCostLedger.objects.create(
            scope=scope or self.scope,
            period=period or self.period,
            token_budget=int(amount),
            updated_by=actor,
            timestamp=timezone.now(),
            tokens_used=0,
            stage="",
            idempotency_key=f"budget-{uuid.uuid4()}",
        )

    def record_spend(
        self,
        stage,
        tokens_used,
        amount=None,
        link=None,
        table=None,
        idempotency_key=None,
        period=None,
        scope=None,
        links=None,
    ):
        key = idempotency_key or f"{stage}-{uuid.uuid4()}"
        row, created = LlmCostLedger.objects.get_or_create(
            idempotency_key=key,
            defaults={
                "scope": scope or self.scope,
                "period": period or self.period,
                "tokens_used": int(tokens_used),
                "amount": amount,
                "stage": stage,
                "link_ref": link,
                "table_ref": table,
                "timestamp": timezone.now(),
            },
        )
        if links is not None:
            row.links.set(links)
        return row, created

    def exhausted(self, stage, link=None, links=None):
        """Park ``link`` and notify the admin (FR-048, FR-049)."""
        from notifications.interfaces import NotificationsInterface

        affected = list(links or ([] if link is None else [link]))
        if affected:
            Link.objects.filter(pk__in=[item.pk for item in affected]).update(
                pipeline_stage=Link.PipelineStage.AWAITING_LLM_BUDGET,
                last_error=f"awaiting_llm_budget:{stage}",
            )
        NotificationsInterface.notify(
            event_type="llm_budget_exhausted",
            subject="LLM token budget exhausted",
            body=f"Stage '{stage}' is waiting for the token budget to be restored.",
            related_object=(
                f"admin_console.LinkBatch:{','.join(str(item.pk) for item in affected)}"
                if len(affected) > 1
                else f"admin_console.Link:{affected[0].pk}" if affected else ""
            ),
            dedup_key=f"budget:{stage}:{timezone.now().date()}",
        )

    def guard(self, stage, link=None, links=None, scope=None, period=None):
        if not self.allows(scope, period):
            self.exhausted(stage, link=link, links=links)
            raise LlmBudgetExhausted(stage)


class LlmClient:
    """The single place an LLM call is made for the pipeline stages."""

    def __init__(self, budget=None, model=None):
        self.budget = budget or LlmBudget()
        self.model = model or settings.OPENAI_MODEL

    def chat_json(
        self,
        system,
        user,
        *,
        stage,
        idempotency_key=None,
        model=None,
        link=None,
        table=None,
        links=None,
        response_model=None,
        strict_schema=False,
    ):
        self.budget.guard(stage, link=link, links=links)
        base_url = (settings.OPENAI_BASE_URL or "").rstrip("/")
        if not base_url:
            raise LlmError("OPENAI_BASE_URL is not configured")
        response_format = {"type": "json_object"}
        if strict_schema:
            if response_model is None:
                raise ValueError("strict_schema requires response_model")
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "plan_extraction",
                    "strict": True,
                    "schema": _strict_json_schema(response_model),
                },
            }
        payload = {
            "model": model or self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": response_format,
            "temperature": 0,
            "prompt_cache_key": (
                f"{stage}:{idempotency_key}" if idempotency_key else stage
            ),
        }
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmError(str(exc)) from exc
        body = response.json()
        usage = body.get("usage") or {}
        cached_tokens = (usage.get("prompt_tokens_details") or {}).get(
            "cached_tokens", 0
        )
        self.budget.record_spend(
            stage,
            max(0, usage.get("total_tokens", 0) - cached_tokens),
            link=link,
            table=table,
            links=links,
            idempotency_key=idempotency_key,
        )
        content = body["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
        except (ValueError, KeyError) as exc:
            raise LlmError(f"unparseable LLM response: {content[:200]}") from exc
        if response_model is not None:
            try:
                data = response_model.model_validate(data).model_dump(mode="json")
            except ValidationError as exc:
                raise LlmError(
                    "LLM response did not match the required JSON schema"
                ) from exc
        return data

    def classify_tables(self, table_contexts, *, idempotency_key=None, link=None):
        """Classify tables individually before labeling and schema extraction."""
        verdicts = []
        for context in table_contexts:
            chunk_key = (
                f"{idempotency_key}:{context['table_index']}"
                if idempotency_key
                else None
            )
            verdicts.extend(
                self._classify_extract_batch(
                    [context], idempotency_key=chunk_key, link=link
                )
            )
        return verdicts

    def _classify_extract_batch(
        self, table_contexts, *, idempotency_key=None, link=None
    ):
        """Classify one table in one LLM request."""
        schema_summary = {
            key: [
                {
                    "key": field.key,
                    "kind": field.kind,
                    "required": field.required,
                    "allowed_values": list(field.values),
                }
                for field in schema.fields
            ]
            for key, schema in plan_schema.PLAN_SCHEMA.items()
        }
        system = (
            "You receive one extracted table. Determine whether it is a correct plan "
            "table for one of the supported schema types. A correct table presents named "
            "plans/packages and their details or pricing that can be mapped to one exact "
            "schema key. If it is not a plan table or no schema fits, return only "
            'table_index and "is_correct": false for that table. If it is correct, return '
            'table_index and "is_correct": true, its exact plan_type, and "confidence". '
            "Do not return plans. Supported schemas: "
            f"{json.dumps(schema_summary, ensure_ascii=False)}. Return JSON with a tables "
            "array containing exactly one result."
        )
        raw = self.chat_json(
            system,
            json.dumps({"tables": table_contexts}, ensure_ascii=False),
            stage="classification",
            idempotency_key=idempotency_key,
            link=link,
        )
        try:
            response = CombinedTablesOut.model_validate(raw)
        except ValidationError as exc:
            raise LlmError("LLM response did not match combined table schema") from exc
        expected = {context["table_index"] for context in table_contexts}
        by_index = {}
        raw_by_index = {}
        for item, raw_item in zip(response.tables, raw["tables"]):
            if item.table_index in by_index:
                continue
            by_index[item.table_index] = item
            raw_by_index[item.table_index] = raw_item
        results = []
        for table_index in sorted(expected):
            item = by_index.get(table_index)
            if item is None:
                # The model skipped this table's verdict; treat it as not a plans table
                # rather than failing the whole link.
                results.append(
                    CombinedTableOut(table_index=table_index, is_correct=False)
                )
                continue
            source = raw_by_index[table_index]
            if item.is_correct and (
                item.plan_type not in plan_schema.PLAN_SCHEMA
                or "plan_type" not in source
            ):
                item.is_correct = False
                item.plan_type = None
            if item.is_correct and item.classification_confidence is None:
                item.classification_confidence = 0.0
            results.append(item)
        return results

    def extract_plans(
        self,
        table_context,
        plan_type,
        field_keys,
        *,
        idempotency_key=None,
        link=None,
        table=None,
    ):
        """Extract a **list of plans** as data against the schema (FR-026, FR-028)."""
        model = plan_schema.list_model(plan_type)
        if model is None:
            raise LlmError(f"unknown plan schema: {plan_type}")
        system = (
            "You extract product or service plan data from a table as JSON using the selected "
            "plan schema. Produce DATA only: "
            "no selectors and no formulas. Normalize amounts, units, and billing periods. "
            "Treat each table row as a separate plan; map cells by column headers, not by "
            "assuming a fixed column order. Headers may be Persian or English and prices "
            "may include localized digits, separators, or currency words. Normalize those "
            "to a numeric price_amount in toman, converting Persian and Arabic-Indic digits. "
            "The price_amount unit is always toman: if a price is stated in thousand toman "
            "(including هزار تومان or هزار تومن), multiply the stated number by 1,000; "
            "if stated in million toman, multiply by 1,000,000. Do not leave the scale implicit. "
            "Price amount and scale may be in separate adjacent columns: combine the amount "
            "with its unit/scale columns before normalizing (for example 15,490 under a "
            "million toman scale means 15,490,000,000 toman; do not multiply by both thousand "
            "and million when both labels describe the same price). Headers such as قیمت ماهیانه, "
            "هزار تومان, and میلیون تومان may jointly describe one price. "
            "Every plan must have a non-empty plan_name and a numeric price_amount. "
            "Never use 0, an empty string, or a guessed value to represent a missing price; "
            "if a row has no explicit price, omit that row from the plans list. Only return "
            "a zero price when the source explicitly states that the plan is free. "
            "Other specifications may be unknown; use null or omit them rather than guessing. "
            "For virtual_server plans, map hardware into these named fields whenever present: "
            "CPU model to cpu_model, core count to cpu_cores, RAM size as a number to "
            "ram_amount and its unit to ram_unit, RAM generation to ram_type, disk capacity "
            "per disk as a number to disk_amount and its unit to disk_unit, disk count to "
            "disk_count, and SSD/NVMe/HDD/SAS technology to disk_type. For example, "
            "'2 * 512GB SSD' means disk_count=2, disk_amount=512, disk_unit='GB', "
            "disk_type='SSD'; '32GB DDR4' means ram_amount=32, ram_unit='GB', "
            "ram_type='DDR4'; 'Intel Core i7-6700 (4 Core)' means cpu_model='Intel Core i7-6700' "
            "and cpu_cores=4. Use these fields instead of placing those facts in other. "
            "Set confidence to 1.0 when the plan name and price are explicitly present in "
            "the corresponding row and mapped unambiguously; optional missing CPU, RAM, "
            "storage, OS, or billing details do not lower confidence. Use below 1.0 only "
            "when name or price is ambiguous, inferred, or unsupported. Do not invent plans. "
            "Every plan item must contain a 'values' object with the schema fields; "
            "never put plan fields directly at the item top level. Any meaningful table "
            "column that does not map to a field in the selected schema must be preserved "
            "in values.other as an array of {key, value} objects. Use the original column "
            "header as key (preserve Persian headers in Persian) and the cell content as "
            "value; do not translate, discard, or invent these facts. In particular, keep "
            "each server specification such as CPU, RAM (e.g. 32GB DDR4), disks (e.g. "
            "2 * 512GB SSD), location, traffic, setup fee, support, datacenter, and delivery "
            "time in other when it is not represented by a schema field. Never omit these "
            "technical facts just because their source headers are unusual or machine-generated. "
            f"The output is a LIST of plans; each plan uses these field keys for plan type "
            f"'{plan_type}': {sorted(field_keys)}. "
            'Return JSON: {"plans": [{"values": {field_key: value}, "confidence": number}]}.'
        )
        user = json.dumps({"table": table_context}, ensure_ascii=False)
        data = self.chat_json(
            system,
            user,
            stage="schema_extraction",
            idempotency_key=idempotency_key,
            link=link,
            table=table,
        )
        raw_plans = data.get("plans", [])
        if not isinstance(raw_plans, list):
            raise LlmError("LLM returned plans in an invalid format")
        plans = []
        for index, item in enumerate(raw_plans):
            try:
                raw_values = (
                    item.get("values", item) if isinstance(item, dict) else item
                )
                values = _sanitize_plan_values(raw_values, plan_type)
                if values is None:
                    continue
                plan = PlanRecordOut(
                    values=values,
                    confidence=(
                        item.get("confidence", 1.0) if isinstance(item, dict) else 1.0
                    ),
                )
            except ValidationError, TypeError:
                logger.warning(
                    "llm_plan_record_skipped",
                    extra={
                        "event": "llm_plan_record_skipped",
                        "record_index": index,
                        "table_id": getattr(table, "pk", None),
                    },
                )
                continue
            plans.append(plan)
        if raw_plans and not plans:
            raise LlmError("LLM returned no valid plan records")
        return plans


default_budget = LlmBudget()
default_client = LlmClient(budget=default_budget)


def current_budget(scope="global", period="monthly"):
    return default_budget.current_budget(scope, period)


def tokens_used(scope="global", period="monthly"):
    return default_budget.tokens_used(scope, period)


def budget_allows(scope="global", period="monthly"):
    return default_budget.allows(scope, period)


def set_token_budget(amount, period="monthly", scope="global", actor=None):
    return default_budget.set_budget(amount, period=period, scope=scope, actor=actor)


def budget_exhausted(stage, link=None):
    return default_budget.exhausted(stage, link=link)


def record_llm_spend(*args, **kwargs):
    return default_budget.record_spend(*args, **kwargs)


def classify_tables(*args, **kwargs):
    return default_client.classify_tables(*args, **kwargs)


def extract_plans(*args, **kwargs):
    return default_client.extract_plans(*args, **kwargs)
