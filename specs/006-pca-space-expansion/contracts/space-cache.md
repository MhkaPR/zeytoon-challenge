# Internal Contract: Recommendation Space Cache

No public HTTP contract changes. Catalogue and signal APIs stay as in feature 005.

## Cache Key

```text
recommendations:space:v1:<version>
```

One bundle per corpus/configuration version. The version includes plan count, latest
publish time, a hash of `(id, title)` pairs, and the semantic configuration.

## Bundle

```json
{
  "version": "string",
  "space": "fitted PlanSpace",
  "values": "2-D float array",
  "masks": "2-D float array",
  "ids": [1, 2],
  "published_at": ["2026-11-07T10:00:00+00:00"]
}
```

`values` and `masks` must have equal shape and finite values.

## Refresh

```text
python manage.py refresh_recommendation_space
```

The command enqueues `refresh_plan_space_task`. The task fits the space, validates it,
and writes the cache key. On failure it logs `recommendation_space_refresh_failed` and
does not write, leaving the previous key available.
