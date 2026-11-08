# catalog — API

Base path: `/api/v1/catalog`

All endpoints are public (no authentication required).

## `GET /site-config`

Returns frontend runtime configuration.

```json
{
  "catalog": {
    "priceMin": 300000,
    "priceMax": 1500000,
    "priceStep": 50000,
    "pageSizes": [8, 12],
    "defaultPageSize": 8,
    "resourceOptions": {
      "ram": [1, 2, 4, 8, 16, 32, 64],
      "cpu": [1, 2, 4, 8, 16],
      "disk": [20, 50, 100, 250, 500, 1000],
      "traffic": [100, 500, 1000, 2000, 5000, 10000]
    },
    "companyFilterVisible": 5
  },
  "ops": {
    "siteRefreshMs": 8000,
    "linksRefreshMs": 5000,
    "captureDefaultDurationMs": 15000
  },
  "contact": {"email": "...", "phone": "...", "address": "..."},
  "social": {"instagram": "...", "telegram": "...", "linkedin": "...", "github": "..."}
}
```

## `GET /plans`

Public published plans.

Query parameters:

| Parameter | Purpose |
|---|---|
| `q` | free-text search where supported by the filter |
| `type` | plan type (`host`, `virtual_server`, `dedicated_server`, `cdn` aliases) |
| `company` | provider/company filter |
| `sort` | `price`, `expensive`, `relevance`, or default related order |
| `page` / `page_size` | pagination (`page_size` capped at 12) |
| resource filters | normalized RAM/CPU/disk/traffic ranges |
| `os`, `location` | categorical facets |

Response:

```json
{
  "data": [
    {
      "id": 1,
      "domain": "example.com",
      "company_name": "Example Co",
      "plan_type": "hosting",
      "values": {"plan_name": "Business", "price_amount": 250000},
      "url": "https://example.com/plans",
      "published_at": "2026-01-01T10:00:00+03:30"
    }
  ],
  "page": {
    "count": 1,
    "page": 1,
    "page_size": 12,
    "total_pages": 1,
    "facets": {}
  }
}
```

Personalization uses `X-Visitor-Id` or the `visitor_id` cookie.

## `GET /companies`

Providers with published plans.

```json
{
  "data": [{"domain": "example.com", "company_name": "Example Co", "plan_count": 12}],
  "page": {"count": 1, "page": 1, "page_size": 12, "total_pages": 1}
}
```

## `GET /companies/recent`

Up to three verified companies created since the start of the current month.

```json
{
  "companies": [
    {"domain": "example.com", "company_name": "Example Co", "created_at": "2026-01-01T10:00:00+03:30"}
  ]
}
```
