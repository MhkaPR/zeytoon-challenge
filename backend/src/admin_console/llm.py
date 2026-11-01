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
from pathlib import Path
import uuid
from typing import Literal

import httpx
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from admin_console import plan_schema
from admin_console.models import Link, LlmCostLedger

PROMPT_VERSION = "v2"
PLAN_EXTRACTION_PROMPT_PATH = Path(__file__).with_name("prompts") / "plan_extraction.md"
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


def _plan_extraction_system_prompt(plan_type):
    try:
        instructions = PLAN_EXTRACTION_PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise LlmError("plan extraction system prompt could not be loaded") from exc
    guidance = json.dumps(_schema_field_guidance(plan_type), ensure_ascii=False)
    return (
        f"{instructions.strip()}\n\n"
        f"Selected plan type: {plan_type}. Use this field guidance from the active schema: {guidance}"
    )


class LlmError(Exception):
    """The provider was reachable but returned an unusable response."""


class NoPlanRecordsError(LlmError):
    """Extraction ran successfully but no plan met the quality requirements."""


class LlmBudgetExhausted(Exception):
    """The token budget is exhausted, so no LLM call may be made (FR-048)."""


class RefilterVerdict(BaseModel):
    is_plans_page: bool
    plan_type: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class TableClassificationOut(BaseModel):
    table_index: int
    is_plans_table: bool
    plan_type: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class PlanRecordOut(BaseModel):
    values: dict
    confidence: float | None = None


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

    def record_spend(self, stage, tokens_used, amount=None, link=None, table=None,
                     idempotency_key=None, period=None, scope=None):
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
        return row, created

    def exhausted(self, stage, link=None):
        """Park ``link`` and notify the admin (FR-048, FR-049)."""
        from notifications.interfaces import NotificationsInterface

        if link is not None:
            Link.objects.filter(pk=link.pk).update(
                pipeline_stage=Link.PipelineStage.AWAITING_LLM_BUDGET,
                last_error=f"awaiting_llm_budget:{stage}",
            )
        NotificationsInterface.notify(
            event_type="llm_budget_exhausted",
            subject="LLM token budget exhausted",
            body=f"Stage '{stage}' is waiting for the token budget to be restored.",
            related_object=f"admin_console.Link:{link.pk}" if link else "",
            dedup_key=f"budget:{stage}:{timezone.now().date()}",
        )

    def guard(self, stage, link=None, scope=None, period=None):
        if not self.allows(scope, period):
            self.exhausted(stage, link=link)
            raise LlmBudgetExhausted(stage)


class LlmClient:
    """The single place an LLM call is made for the pipeline stages."""

    def __init__(self, budget=None, model=None):
        self.budget = budget or LlmBudget()
        self.model = model or settings.OPENAI_MODEL

    def chat_json(self, system, user, *, stage, idempotency_key=None, model=None,
                  link=None, table=None, response_model=None, strict_schema=False):
        self.budget.guard(stage, link=link)
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
        }
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        try:
            response = httpx.post(
                f"{base_url}/chat/completions", json=payload, headers=headers, timeout=60.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmError(str(exc)) from exc
        body = response.json()
        usage = body.get("usage") or {}
        self.budget.record_spend(
            stage,
            usage.get("total_tokens", 0),
            link=link,
            table=table,
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
                raise LlmError("LLM response did not match the required JSON schema") from exc
        return data

    def refilter_page(self, url, headings, important_section, *, idempotency_key=None,
                      link=None):
        system = (
            "You decide whether a web page lists hosting/server plans for sale. "
            "You receive only a URL, its headings, and its most important text block. "
            'Return JSON: {"is_plans_page": bool, "plan_type": string, '
            '"confidence": number in [0,1]}.'
        )
        user = json.dumps(
            {"url": url, "headings": headings, "important_section": important_section},
            ensure_ascii=False,
        )
        data = self.chat_json(system, user, stage="refilter",
                              idempotency_key=idempotency_key, link=link)
        return RefilterVerdict(**data)

    def classify_tables(self, table_contexts, *, idempotency_key=None, link=None):
        plan_type = Literal["", *plan_schema.PLAN_SCHEMA.keys()]
        classification_model = create_model(
            "TableClassificationStrict",
            __config__=ConfigDict(extra="forbid"),
            table_index=(int, ...),
            is_plans_table=(bool, ...),
            plan_type=(plan_type, ...),
            confidence=(float, ...),
        )
        response_model = create_model(
            "TableClassificationsStrict",
            __config__=ConfigDict(extra="forbid"),
            classifications=(list[classification_model], ...),
        )
        system = (
            "You classify tables. For each table decide if it lists hosting/server plans "
            '(plans table) or not. If plans, plan_type MUST be one exact schema key from '
            f"{sorted(plan_schema.PLAN_SCHEMA)}. If none matches, mark not a plans table and "
            'return an empty plan_type. Never return a descriptive category label. '
            'Return JSON: {"classifications": [{"table_index": int, '
            '"is_plans_table": bool, "plan_type": string, "confidence": number}]}.'
        )
        user = json.dumps({"tables": table_contexts}, ensure_ascii=False)
        data = self.chat_json(system, user, stage="classification",
                              idempotency_key=idempotency_key, link=link,
                              response_model=response_model)
        return [TableClassificationOut(**item) for item in data.get("classifications", [])]

    def extract_plans(self, table_context, plan_type, field_keys, *, idempotency_key=None,
                      link=None, table=None):
        """Extract a **list of plans** as data against the schema (FR-026, FR-028)."""
        output_model = plan_schema.extraction_model(plan_type)
        if output_model is None:
            raise LlmError(f"unknown plan schema: {plan_type}")
        system = _plan_extraction_system_prompt(plan_type)
        user = json.dumps({"table": table_context}, ensure_ascii=False)
        data = self.chat_json(
            system,
            user,
            stage="schema_extraction",
            idempotency_key=idempotency_key,
            link=link,
            table=table,
            response_model=output_model,
            strict_schema=True,
        )
        raw_plans = data.get("plans", [])
        if not isinstance(raw_plans, list):
            raise LlmError("LLM returned plans in an invalid format")
        model = plan_schema.list_model(plan_type)
        allowed_fields = plan_schema.all_field_keys(plan_type)
        plans = []
        for index, item in enumerate(raw_plans):
            try:
                plan = PlanRecordOut.model_validate(item)
                if model is not None:
                    model.model_validate({"plans": [plan.values]})
            except (ValidationError, TypeError):
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


def _schema_field_guidance(plan_type):
    schema = plan_schema.schema_for(plan_type)
    if schema is None:
        return []
    return [
        {
            "key": field.key,
            "label": field.label,
            "kind": field.kind,
            "unit_family": field.unit_family,
            "canonical_unit": field.canonical_unit,
            "values": list(field.values),
            "aliases": list(field.aliases),
        }
        for field in schema.fields
        if field.key in plan_schema.all_field_keys(plan_type)
    ]


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


def refilter_page(*args, **kwargs):
    return default_client.refilter_page(*args, **kwargs)


def classify_tables(*args, **kwargs):
    return default_client.classify_tables(*args, **kwargs)


def extract_plans(*args, **kwargs):
    return default_client.extract_plans(*args, **kwargs)
