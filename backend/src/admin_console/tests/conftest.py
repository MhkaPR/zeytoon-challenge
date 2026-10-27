"""Shared pytest fixtures for the admin console tests."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import ensure_role_groups
from companies import services as company_services

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Keep DRF throttle counters out of the shared Redis cache between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _artifact_storage(tmp_path, settings):
    """Route artifact writes to a throwaway filesystem backend (no S3 in tests)."""
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
    from admin_console.models import Site

    return Site.objects.create(
        company=approved_company,
        domain=approved_company.domain,
    )


@pytest.fixture
def kept_link(site):
    from admin_console.models import Link

    return Link.objects.create(
        site=site,
        url="https://example.com/plans",
        url_hash="kept-hash",
        source=Link.Source.SITEMAP,
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.CAPTURE,
    )


@pytest.fixture
def traced_link(kept_link, operator):
    """A kept link with a stored, valid trace (for extraction/labeling tests)."""
    from django.utils import timezone

    from admin_console import artifacts
    from admin_console.models import Trace
    from admin_console.tests.factories import make_trace_bytes

    data = make_trace_bytes(url=kept_link.url)
    key, backend, size, digest = artifacts.save_trace(data)
    trace = Trace.objects.create(
        link=kept_link,
        captured_by=operator,
        captured_at=timezone.now(),
        storage_key=key,
        storage_backend=backend,
        byte_size=size,
        content_sha256=digest,
        is_valid_trace=True,
    )
    kept_link.current_trace = trace
    kept_link.save(update_fields=["current_trace", "updated_at"])
    return kept_link


@pytest.fixture
def published_link(operator_client, traced_link):
    """A link with extracted tables, a complete recipe, and published catalog rows."""
    from admin_console.models import Link

    site = traced_link.site
    site.maintenance_state = site.MaintenanceState.ACTIVE
    site.save(update_fields=["maintenance_state", "updated_at"])

    operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    tables = operator_client.get(f"/api/v1/ops/links/{traced_link.pk}/tables").json()[
        "tables"
    ]
    table = tables[0]
    column = dict(table["columns"][0])
    required = (
        "plan_name",
        "storage_amount",
        "storage_unit",
        "ram_amount",
        "cpu_cores",
        "bandwidth_amount",
        "price_amount",
        "billing_period",
    )
    bindings = [
        {
            "schema_field_key": key,
            "source_table_id": table["id"],
            "source_column_id": column["id"],
            "selector": column["path"],
            "formula": "",
        }
        for key in required
    ]
    operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {"plan_type": "hosting", "bindings": bindings},
        format="json",
    )
    operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/publish")
    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage == Link.PipelineStage.PUBLISHED
    return traced_link
