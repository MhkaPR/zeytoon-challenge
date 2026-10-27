"""Artifact storage tests (US3, FR-000a, research R4)."""

import pytest
from django.core.files.storage import storages

from admin_console import artifacts
from admin_console.models import Trace

pytestmark = pytest.mark.django_db


def test_save_open_delete_round_trip():
    data = b'{"snapshot": {"node": {}}, "records": []}'
    key, backend, size, digest = artifacts.save_trace(data)
    assert key.startswith("traces/") and key.endswith(".json")
    assert backend == "default"
    assert size == len(data)
    assert len(digest) == 64
    assert artifacts.read_trace(key) == data
    with artifacts.open_trace(key) as handle:
        assert handle.read() == data
    assert artifacts.delete_trace(key) is True
    assert storages["default"].exists(key) is False


def test_uuid_keys_do_not_collide():
    key1, *_ = artifacts.save_trace(b"a")
    key2, *_ = artifacts.save_trace(b"a")
    assert key1 != key2


def test_materialize_round_trips_bytes():
    data = b'{"snapshot": {"node": {}}}'
    key, *_ = artifacts.save_trace(data)
    path = artifacts.materialize(key)
    with open(path, "rb") as handle:
        assert handle.read() == data


def test_no_trace_column_holds_the_body():
    field_names = {f.name for f in Trace._meta.get_fields()}
    assert "content" not in field_names
    assert "body" not in field_names
    assert "data" not in field_names
