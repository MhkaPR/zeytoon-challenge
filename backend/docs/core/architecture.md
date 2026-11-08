# core — Architecture

## 1. Responsibility

`apps.core` provides helpers that turn django-constance values into the public frontend
configuration payload and the flat operator settings snapshot.

It has **no models, views, URLs, or registered app**. It is imported as a plain module by
`catalog` and `admin_console`.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `site_config.py` | `public_site_config()`, `settings_snapshot()` |
| `apps.py` | `CoreConfig` (not listed in `INSTALLED_APPS`) |
| `models/__init__.py` | intentionally empty |
| `views.py`, `admin.py`, `tests.py` | scaffold placeholders |

## 3. Public payload

`public_site_config()` returns:

- `catalog`: price bounds/step, page sizes, resource options, provider filter visibility;
- `ops`: site/link polling intervals and default capture duration;
- `contact`: email, phone, address;
- `social`: Instagram, Telegram, LinkedIn, GitHub.

Values are coerced and defaulted so a malformed constance value cannot break the frontend.

## 4. Operator snapshot

`settings_snapshot()` returns a flat key/value map used by the operator settings endpoint.
It includes the catalog/ops/contact/social values; the console merges pipeline-specific
values on top.

## 5. Why it is not an installed app

`core` is a module-level concern, not a domain. Keeping it out of `INSTALLED_APPS` avoids
empty migrations and makes the dependency direction explicit: catalog/console import
`apps.core.site_config`, and `core` imports nothing from them.
