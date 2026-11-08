# utils — Architecture

## 1. Responsibility

`apps.utils` contains shared infrastructure used by every app:

- the abstract timestamped/soft-delete base model and managers;
- structured JSON logging with secret redaction;
- the shared pagination envelope;
- serializer input parsing and envelope serializers;
- the list-view base class;
- audit-log registration for project models.

It contains no domain logic.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `models/base.py` | `TimestampedModel` |
| `models/soft_delete.py` | `SoftDeleteManager`, `DeletedObjectsManager`, `SoftDeleteConflict` |
| `logging.py` | `SensitiveDataFilter`, `JsonFormatter`, `mask_text` |
| `pagination.py` | `EnvelopePageNumberPagination` |
| `serializers.py` | `parse_input`, `PageMetaSerializer`, `PaginatedResponseSerializer` |
| `views.py` | `EnvelopeListViewSet` |
| `apps.py` | `UtilsConfig.ready()` registers auditlog for project apps |

## 3. Soft delete

Every model inherits `TimestampedModel`:

- `objects` → active rows (`deleted_at IS NULL`);
- `deleted_objects` → soft-deleted rows;
- `delete()` → sets `deleted_at`, but first checks required relations and raises
  `SoftDeleteConflict` if a non-null FK still references the row;
- `hard_delete()` → physical delete.

`SoftDeleteQuerySet.delete()` also soft-deletes in bulk.

## 4. Logging

- `JsonFormatter` emits one JSON object per record with level, logger, message, time, and
  selected extras (`event`, `phone`, `provider`, `duration_ms`).
- `SensitiveDataFilter` redacts JWT-like tokens and `code`/`otp`/`token` key-value pairs.
- Phone numbers are treated as ordinary identifiers and are not redacted.

## 5. Pagination and envelopes

`EnvelopePageNumberPagination`:

- default page size `12`, max page size `12`;
- `page_size` query parameter;
- response `{data, page}` with `count`, `page`, `page_size`, `total_pages`.

`EnvelopeListViewSet` centralizes list pagination and lets domain views override
`serialize_page()` and `get_page_extra()`.

## 6. Input parsing

`parse_input(serializer_cls, data)` validates with DRF and raises `ApiError` with the
offending field names, keeping every view on the same error contract.

## 7. Audit logging

`UtilsConfig.ready()` registers every non-proxy model in `accounts`, `companies`,
`admin_console`, `catalog`, `pipeline`, and `recommendations` with `django-auditlog`.
