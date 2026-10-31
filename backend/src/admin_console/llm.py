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
import uuid

import httpx
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field

from admin_console import plan_schema
from admin_console.models import Link, LlmCostLedger

PROMPT_VERSION = "v1"


class LlmError(Exception):
    """The provider was reachable but returned an unusable response."""


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
        self.model = model

    def chat_json(self, system, user, *, stage, idempotency_key=None, model=None,
                  link=None, table=None):
        self.budget.guard(stage, link=link)
        base_url = (settings.OPENAI_BASE_URL or "").rstrip("/")
        if not base_url:
            raise LlmError("OPENAI_BASE_URL is not configured")
        payload = {
            "model": model or self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
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
            return json.loads(content)
        except (ValueError, KeyError) as exc:
            raise LlmError(f"unparseable LLM response: {content[:200]}") from exc

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
        system = (
            "You classify tables. For each table decide if it lists hosting/server plans "
            '(plans table) or not. Return JSON: {"classifications": [{"table_index": int, '
            '"is_plans_table": bool, "plan_type": string, "confidence": number}]}.'
        )
        user = json.dumps({"tables": table_contexts}, ensure_ascii=False)
        data = self.chat_json(system, user, stage="classification",
                              idempotency_key=idempotency_key, link=link)
        return [TableClassificationOut(**item) for item in data.get("classifications", [])]

    def extract_plans(self, table_context, plan_type, field_keys, *, idempotency_key=None,
                      link=None, table=None):
        """Extract a **list of plans** as data against the schema (FR-026, FR-028)."""
        system = (
            "You extract hosting/server plan data from a table as JSON. Produce DATA only: "
            "no selectors and no formulas. Normalize amounts, units, and billing periods. "
            f"The output is a LIST of plans; each plan uses these field keys for plan type "
            f"'{plan_type}': {sorted(field_keys)}. "
            'Return JSON: {"plans": [{"values": {field_key: value}, "confidence": number}]}.'
        )
        user = json.dumps({"table": table_context}, ensure_ascii=False)
        data = self.chat_json(system, user, stage="schema_extraction",
                              idempotency_key=idempotency_key, link=link, table=table)
        plans = [PlanRecordOut(**item) for item in data.get("plans", [])]
        model = plan_schema.list_model(plan_type)
        if model is not None:
            model.model_validate({"plans": [plan.values for plan in plans]})
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


def refilter_page(*args, **kwargs):
    return default_client.refilter_page(*args, **kwargs)


def classify_tables(*args, **kwargs):
    return default_client.classify_tables(*args, **kwargs)


def extract_plans(*args, **kwargs):
    return default_client.extract_plans(*args, **kwargs)
