# catalog — Workflow

## 1. Publish a plan record

Called by the pipeline, not by HTTP clients:

```text
CatalogInterface.upsert_published_record(
  source="admin_console",
  site=..., link=..., trace=..., classification=...,
  plan_type=..., natural_key=..., values=...
)
  → update_or_create keyed by (source, site, natural_key)
  → is_published=True, published_at=now, retired_at=None
```

## 2. Retire a plan record

```text
CatalogInterface.retire_published_record(source, site, natural_key)
  → is_published=False, retired_at=now
```

The pipeline retires natural keys that disappeared from a re-extraction so stale values
are never served.

## 3. List public plans

`GET /api/v1/catalog/plans`

```text
queryset = PublishedRecord(is_published=True).order_by(-published_at, id)
  → apply PublishedPlanFilter (type, company, resources, price, OS, location, ...)
  → if sort in {price, expensive, relevance}: deterministic list path
  → else:
      records = list(filtered queryset)
      ordered_ids = RecommendationsInterface.rank(
          CatalogInterface.published_plan_records(),
          [record.pk for record in records],
          visitor_id, user,
      )
      reorder records, append any unranked records
  → paginate
  → enrich each record with site/company identity and source URL
  → attach facets to the page object
```

Visitor identity comes from the `X-Visitor-Id` header or the `visitor_id` cookie.

## 4. List public companies

`GET /api/v1/catalog/companies`

```text
group PublishedRecord by site
  → plan_count = count(records)
  → optional q filter over site domain/company name
  → order by plan_count desc
  → enrich with pipeline site details
```

## 5. Recent companies

`GET /api/v1/catalog/companies/recent`

```text
PipelineInterface.public_recent_companies(month_start)
  → verified, non-archived companies created since the start of the month
  → newest first, max 3
```

## 6. Site configuration

`GET /api/v1/catalog/site-config`

```text
public_site_config()
  → catalog options
  → ops polling intervals
  → contact details
  → social URLs
```

## 7. Pagination contract

```json
{
  "data": [],
  "page": {
    "count": 0,
    "page": 1,
    "page_size": 12,
    "total_pages": 1,
    "facets": {
      "companies": [],
      "operating_systems": [],
      "locations": [],
      "resources": {"ram": [], "cpu": [], "disk": [], "traffic": []},
      "resource_units": {"ram": "GB", "cpu": "core", "disk": "GB", "traffic": "GB"}
    }
  }
}
```
