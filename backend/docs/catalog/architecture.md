# catalog — Architecture

## 1. Responsibility

`apps.catalog` is the **public read model** for published plans. It owns:

- the `PublishedRecord` table that the pipeline publishes into;
- the only write paths for published records (`upsert`, `retire`);
- public plan listing, filtering, facets, and related ordering;
- public company listing and recent-company listing;
- the public site-configuration endpoint consumed by the frontend.

It never imports `admin_console`. Provenance fields (`site`, `link`, `trace`,
`classification`) are opaque integers so catalog stays decoupled from pipeline tables.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `models/published_record.py` | `PublishedRecord` |
| `services/v1/catalog.py` | upsert, retire, published keys/count |
| `interfaces.py` | `CatalogInterface` used by pipeline and recommendations |
| `filters.py` | `PublishedPlanFilter`, resource normalization, aliases, units |
| `serializers/v1/catalog.py` | public plan/company/facet serializers |
| `views/v1/catalog.py` | site-config, plans, companies, recent companies |
| `urls.py` | `/api/v1/catalog/` routes |

## 3. Read model

```text
pipeline PlanRecord
      │ publish_link_plans()
      ▼
CatalogInterface.upsert_published_record()
      ▼
PublishedRecord(source="admin_console", site, link, trace, classification, ...)
      ▼
GET /api/v1/catalog/plans
```

A published record is keyed by `(source, site, natural_key)`. Publishing again updates the
values and timestamp; retiring sets `is_published=false` and `retired_at`.

## 4. Filtering and normalization

`filters.py` maps heterogeneous provider values onto canonical filters:

- resource aliases: `ram`, `cpu`, `disk`, `traffic`;
- units normalized to GB (data size) or cores (CPU);
- plan-type aliases (`host`, `virtual_server`, `dedicated_server`, `cdn`);
- numeric values must be positive.

Facets are computed from the filtered queryset and returned inside the pagination `page`
object.

## 5. Related ordering

For the default sort (no explicit `price`/`expensive`/`relevance`):

1. filter the published queryset;
2. load all matching records;
3. ask `RecommendationsInterface.rank()` for an order;
4. paginate the ranked list.

Ranking happens **before pagination**, so pages never repeat or skip items. Explicit price
sorts bypass recommendation ranking.

## 6. Public configuration

`GET /api/v1/catalog/site-config` returns `apps.core.site_config.public_site_config()`:
catalog price/page/resource options, ops polling intervals, contact details, and social
links. All values come from django-constance.

## 7. Dependencies

- `apps.pipeline.interfaces` for site identity, link URLs, and recent companies.
- `apps.recommendations.interfaces` for ranking.
- `apps.core.site_config` for runtime configuration.
- `apps.utils.views.EnvelopeListViewSet` for pagination.
