"""Artifact store on top of Django's STORAGES API (FR-000a, research R4).

Traces and related artifacts are written through the configured ``STORAGES`` backend
(S3-compatible by default, local filesystem selectable from settings) under UUID-based
object keys. No filesystem or S3 code is written by hand (Principle XII).
"""

import hashlib
import tempfile
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import storages


def _trace_key():
    return f"traces/{uuid.uuid4()}.json"


def save_trace(content_bytes, *, key=None, backend="default"):
    """Write trace bytes to the artifact store; return (key, backend, size, sha256)."""
    if isinstance(content_bytes, str):
        content_bytes = content_bytes.encode("utf-8")
    key = key or _trace_key()
    digest = hashlib.sha256(content_bytes).hexdigest()
    storage = storages[backend]
    if storage.exists(key):
        storage.delete(key)
    saved_key = storage.save(key, ContentFile(content_bytes))
    return saved_key, backend, len(content_bytes), digest


def open_trace(key, backend="default"):
    """Return a file-like object for a stored artifact."""
    return storages[backend].open(key, "rb")


def read_trace(key, backend="default"):
    with open_trace(key, backend=backend) as handle:
        return handle.read()


def materialize(key, backend="default", suffix=".json"):
    """Copy a stored artifact to a temporary local file (for domtrack calls).

    domtrack's library API takes local paths; the bridge never converts the trace, it
    only places the same bytes on the local filesystem for the duration of a call.
    """
    handle = tempfile.NamedTemporaryFile(
        mode="wb", suffix=suffix, delete=False
    )
    try:
        with open_trace(key, backend=backend) as source:
            for chunk in iter(lambda: source.read(65536), b""):
                handle.write(chunk)
    finally:
        handle.close()
    return handle.name


def delete_trace(key, backend="default"):
    storage = storages[backend]
    if storage.exists(key):
        storage.delete(key)
        return True
    return False
