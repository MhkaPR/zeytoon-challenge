"""Shared pytest fixtures for the admin console tests."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import ensure_role_groups
from apps.companies import services as company_services

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _artifact_storage(tmp_path, settings):
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path / "artifacts")},
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    yield


@pytest.fixture
def role_groups(db):
    ensure_role_groups()


@pytest.fixture
def owner(db, role_groups):
    user = User.objects.create_user(
        username="+989120000101", phone_number="+989120000101", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))
    return user


@pytest.fixture
def operator(db, role_groups):
    user = User.objects.create_user(
        username="+989120000103", phone_number="+989120000103", password="x"
    )
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))
    return user


def _auth(client, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def auth_client(api_client, owner):
    return _auth(api_client, owner)


@pytest.fixture
def operator_client(api_client, operator):
    return _auth(api_client, operator)


@pytest.fixture
def company(owner):
    return company_services.register_company(
        owner,
        {
            "domain": "example.com",
            "company_name": "Example Hosting",
            "representative_name": "Ali Rezaei",
            "phone_number": "02123456789",
        },
    )


@pytest.fixture
def approved_company(company, operator):
    company_services.record_verification_decision(company, operator, "approved")
    company.refresh_from_db()
    return company


@pytest.fixture
def site(approved_company):
    from apps.pipeline.models import Site

    return Site.objects.create(
        company=approved_company,
        domain=approved_company.domain,
        maintenance_state=Site.MaintenanceState.ACTIVE,
    )


@pytest.fixture
def kept_link(site):
    from apps.pipeline.models import Link

    return Link.objects.create(
        site=site,
        url="https://example.com/plans",
        url_hash="kept-hash",
        source=Link.Source.ADAPTIVE_CRAWL,
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.DISCOVERED,
    )


@pytest.fixture
def traced_link(kept_link):
    from django.utils import timezone

    from apps.pipeline import artifacts
    from apps.pipeline.models import Link, Trace
    from apps.pipeline.tests import factories

    data = factories.make_trace_bytes(url=kept_link.url)
    key, backend, size, digest = artifacts.save_trace(data)
    trace = Trace.objects.create(
        link=kept_link,
        captured_at=timezone.now(),
        storage_key=key,
        storage_backend=backend,
        content_sha256=digest,
        is_valid_trace=True,
    )
    kept_link.current_trace = trace
    kept_link.pipeline_stage = Link.PipelineStage.CAPTURED
    kept_link.save()
    return kept_link


# ---------------------------------------------------------------------------
# External-stage doubles (no network, no browser, no LLM): every stage under
# test is driven through its adapter's ``default_*`` instance, so tests replace
# those methods and inspect exactly what the stage received.
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_llm(monkeypatch):
    """A scripted LLM double for the single classify+extract pass and plan extraction."""
    from apps.pipeline import llm as llm_mod

    stub = SimpleNamespace(
        classifications=[],
        plans=[],
        exhausted_stages=set(),
        combined_classification_calls=[],
        plan_calls=[],
    )

    def _raise_if_exhausted(stage, link=None, links=None):
        if stage in stub.exhausted_stages:
            # Mirror the real client: parking the link and notifying are side effects
            # of the budget guard, so a scripted exhaustion behaves like the real one.
            targets = list(links or ([] if link is None else [link]))
            for target in targets:
                llm_mod.default_budget.exhausted(stage, link=target)
            raise llm_mod.LlmBudgetExhausted(stage)

    def classify_extract_tables(table_contexts, *, idempotency_key=None, link=None):
        stub.combined_classification_calls.append(table_contexts)
        _raise_if_exhausted("classification", link)
        configured = {item["table_index"]: item for item in stub.classifications}
        results = []
        for context in table_contexts:
            verdict = configured.get(
                context["table_index"],
                {
                    "is_plans_table": False,
                    "plan_type": "",
                    "confidence": 0.0,
                },
            )
            accepted = verdict.get("is_correct", verdict.get("is_plans_table", False))
            if (
                not accepted
                or verdict.get("plan_type") not in llm_mod.plan_schema.PLAN_SCHEMA
            ):
                results.append(
                    llm_mod.CombinedTableOut(
                        table_index=context["table_index"], is_correct=False
                    )
                )
                continue
            results.append(
                llm_mod.CombinedTableOut(
                    table_index=context["table_index"],
                    is_correct=True,
                    plan_type=verdict["plan_type"],
                    confidence=verdict.get("confidence", 1.0),
                )
            )
        return results

    def extract_plans(
        table_context,
        plan_type,
        field_keys,
        *,
        idempotency_key=None,
        link=None,
        table=None,
    ):
        stub.plan_calls.append(
            {
                "table": table_context,
                "plan_type": plan_type,
                "field_keys": set(field_keys),
                "link_id": getattr(link, "pk", None),
                "table_id": getattr(table, "pk", None),
            }
        )
        _raise_if_exhausted("schema_extraction", link)
        response = stub.plans
        if callable(response):
            response = response(table_context, plan_type)
        return [
            (
                item
                if isinstance(item, llm_mod.PlanRecordOut)
                else llm_mod.PlanRecordOut(**item)
            )
            for item in response
        ]

    def infer_and_extract_plans(
        table_context, *, idempotency_key=None, link=None, table=None
    ):
        stub.plan_calls.append(
            {
                "table": table_context,
                "plan_type": None,
                "field_keys": set(),
                "link_id": getattr(link, "pk", None),
                "table_id": getattr(table, "pk", None),
            }
        )
        _raise_if_exhausted("schema_extraction", link)
        configured = stub.classifications[0] if stub.classifications else {}
        plan_type = configured.get("plan_type", "hosting")
        response = stub.plans
        if callable(response):
            response = response(table_context, plan_type)
        return plan_type, [
            (
                item
                if isinstance(item, llm_mod.PlanRecordOut)
                else llm_mod.PlanRecordOut(**item)
            )
            for item in response
        ]

    monkeypatch.setattr(
        llm_mod.default_client, "infer_and_extract_plans", infer_and_extract_plans
    )
    monkeypatch.setattr(llm_mod.default_client, "extract_plans", extract_plans)
    return stub


@pytest.fixture
def stub_domtrack(monkeypatch):
    """A domtrack double for capture/extract/label/compare; no browser or disk."""
    from apps.pipeline import domtrack_client, tests

    stub = SimpleNamespace(
        capture_bytes=tests.factories.make_trace_bytes(),
        capture_error=None,
        table_result=tests.factories.domtrack_table_result(),
        labels={"tables": []},
        compare_result=None,
        compare_error=None,
        capture_calls=[],
        extract_calls=[],
        label_calls=[],
        compare_calls=[],
    )

    def capture_headless(url, duration_ms, nav_timeout_ms=None):
        stub.capture_calls.append({"url": url, "duration_ms": duration_ms})
        if stub.capture_error is not None:
            raise stub.capture_error
        return stub.capture_bytes

    def extract_tables(path, min_rows=2, min_cols=2, dedupe=True):
        stub.extract_calls.append(path)
        return stub.table_result

    def label_tables(tables, label_config):
        stub.label_calls.append(tables)
        return stub.labels

    def compare_replay(before_path, replay_config=None, recording=None):
        stub.compare_calls.append(before_path)
        if stub.compare_error is not None:
            raise stub.compare_error
        return stub.compare_result

    monkeypatch.setattr(
        domtrack_client.default_client, "capture_headless", capture_headless
    )
    monkeypatch.setattr(
        domtrack_client.default_client, "extract_tables", extract_tables
    )
    monkeypatch.setattr(domtrack_client.default_client, "label_tables", label_tables)
    monkeypatch.setattr(
        domtrack_client.default_client, "compare_replay", compare_replay
    )
    return stub


@pytest.fixture
def stub_discovery(monkeypatch):
    """A crawl4ai double returning a fixed harvest; returns the stub for assertions."""
    from apps.pipeline import discovery

    stub = SimpleNamespace(urls=[], calls=[])

    def crawl_candidate_links(domain, query, bounds=None):
        stub.calls.append({"domain": domain, "query": query, "bounds": bounds})
        return list(stub.urls)

    monkeypatch.setattr(
        discovery.default_discoverer, "crawl_candidate_links", crawl_candidate_links
    )
    return stub


@pytest.fixture
def no_retry_sleep(monkeypatch):
    """Skip retry backoff so resilience tests stay fast."""
    from apps.pipeline.services.v1 import pipeline as services

    monkeypatch.setattr(services, "_sleep", lambda seconds: None)


@pytest.fixture
def extracted_link(traced_link, stub_domtrack):
    """A link whose current trace has been extracted (one canned table)."""
    from apps.pipeline.services.v1 import pipeline as services

    services.extract_link_tables(traced_link)
    return traced_link


@pytest.fixture
def labeled_link(extracted_link, stub_domtrack):
    """A link whose extracted tables have been labeled (pass 1)."""
    from apps.pipeline.services.v1 import pipeline as services

    services.label_link_tables(extracted_link)
    return extracted_link


HOSTING_PLAN_VALUES = {
    "plan_name": "Starter",
    "storage_amount": 10,
    "storage_unit": "GB",
    "ram_amount": 1,
    "cpu_cores": 1,
    "bandwidth_amount": 100,
    "price_amount": 50000,
    "billing_period": "monthly",
}


@pytest.fixture
def planned_link(labeled_link, stub_llm):
    """A link with one normalized hosting plan record after the combined pass."""
    from apps.pipeline.services.v1 import pipeline as services

    stub_llm.classifications = [
        {
            "table_index": 0,
            "is_correct": True,
            "plan_type": "hosting",
            "confidence": 0.92,
        }
    ]
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]
    services.classify_and_extract_link_tables(labeled_link)
    return labeled_link
