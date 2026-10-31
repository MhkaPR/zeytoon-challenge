"""US4 — traces go through STORAGES under UUID keys, never into a DB column (FR-053)."""

import uuid

import pytest

from admin_console import artifacts
from admin_console.models import Trace
from admin_console.tests import factories

pytestmark = pytest.mark.django_db


def test_save_trace_writes_under_a_uuid_key_and_round_trips():
    data = factories.make_trace_bytes(url="https://example.com/x")

    key, backend, size, digest = artifacts.save_trace(data)

    assert backend == "default"
    assert key.startswith("traces/")
    # The key is UUID-based, so two saves never collide.
    uuid.UUID(key.removeprefix("traces/").removesuffix(".json"))
    assert size == len(data)
    assert artifacts.read_trace(key) == data


def test_delete_trace_removes_the_artifact():
    key, _, _, _ = artifacts.save_trace(factories.make_trace_bytes())
    assert artifacts.delete_trace(key) is True
    assert artifacts.delete_trace(key) is False


def test_trace_model_has_no_body_column(traced_link):
    trace = Trace.objects.get(link=traced_link)
    field_names = {field.name for field in Trace._meta.get_fields()}
    assert "storage_key" in field_names
    assert not (field_names & {"body", "content", "raw", "trace", "data"})
