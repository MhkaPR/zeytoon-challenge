# utils — Workflow

## 1. Soft delete

```text
instance.delete()
  → already deleted? return (0, {})
  → inspect reverse relations:
      skip nullable fields
      skip SET_NULL / SET_DEFAULT / DO_NOTHING
      if a required relation still references the row:
          raise SoftDeleteConflict
  → set deleted_at=now
  → save(update_fields=("deleted_at", "updated_at"))
```

Queries through `objects` then exclude the row; queries through `deleted_objects` include
it.

## 2. API error normalization

```text
ApiError(code, message, http_status, fields)
  → api_exception_handler
  → {"error": {"code", "message", "fields"}}

SoftDeleteConflict
  → 409 conflict

DRF Throttled
  → 429 rate_limited with retry_after_seconds

other DRF exception
  → invalid_request (<500) or server_error (>=500)
```

## 3. Input validation

```text
parse_input(Serializer, request.data)
  → serializer.is_valid()
  → invalid: ApiError(invalid_field, fields=[...])
  → valid: validated_data
```

## 4. List pagination

```text
EnvelopeListViewSet.list()
  → filter_queryset
  → paginate_queryset
  → serialize_page(instances)
  → get_page_extra()
  → {"data": [...], "page": {...}}
```

## 5. Logging

```text
logger.info("event", extra={"event": "...", "phone": "..."})
  → SensitiveDataFilter renders + redacts the message
  → JsonFormatter emits JSON
```

## 6. Audit registration

```text
Django app ready
  → UtilsConfig.ready()
  → auditlog.register(model) for each project model
  → AuditlogMiddleware captures the actor per request
```
