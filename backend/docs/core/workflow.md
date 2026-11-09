# core — Workflow

## 1. Public configuration request

```text
GET /api/v1/catalog/site-config
  → catalog.views.SiteConfigViewSet
  → apps.core.site_config.public_site_config()
  → read constance values
  → coerce ints/lists/dicts with safe defaults
  → return JSON
```

## 2. Operator settings read

```text
GET /api/v1/ops/settings
  → admin_console._settings_snapshot()
  → pipeline constants snapshot
  → apps.core.site_config.settings_snapshot()
  → merged flat map
```

## 3. Operator settings update

```text
PUT /api/v1/ops/settings
  → validate {"values": {...}}
  → for each key that exists on constance.config:
      setattr(config, key, value)
  → return the updated values
```

Unknown keys are ignored rather than written.

## 4. Failure behavior

All coercions fall back to documented defaults, so a bad runtime value degrades the
payload instead of raising. Operators should still correct invalid values in Django admin
or `/ops/settings`.
