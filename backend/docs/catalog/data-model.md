# catalog — Data Model

## PublishedRecord

Table: `catalog_published_record`

| Column | Type | Notes |
|---|---|---|
| `id` | bigint | primary key |
| `site` | int | opaque pipeline site id |
| `link` | int | opaque pipeline link id |
| `trace` | int | opaque pipeline trace id |
| `classification` | int | opaque pipeline classification id |
| `source` | varchar(64) | publisher, default `admin_console` |
| `plan_type` | varchar(64) | e.g. `hosting`, `virtual_server`, `cdn` |
| `natural_key` | varchar(512) | stable identity within a site |
| `values` | JSON | schema-keyed plan data |
| `is_published` | bool | indexed |
| `published_at` | timestamp | |
| `retired_at` | timestamp | set on retire |
| `created_at` / `updated_at` / `deleted_at` | | inherited |

Constraint:

- `uniq_published_record_source_site_key`: unique `(source, site, natural_key)` where
  `deleted_at IS NULL`.

Ordering: newest `published_at` first.

## Value shape

`values` is keyed by the pipeline plan schema, for example:

```json
{
  "plan_name": "Business Hosting",
  "storage_amount": 50,
  "storage_unit": "GB",
  "ram_amount": 4,
  "ram_unit": "GB",
  "cpu_cores": 2,
  "price_amount": 250000,
  "billing_period": "monthly",
  "other": [{"key": "backup", "value": "daily"}]
}
```

The catalog never stores selectors, formulas, or crawl internals.
