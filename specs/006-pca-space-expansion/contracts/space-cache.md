# Internal Contract: Recommendation Space Cache and Refresh

**Feature**: `006-pca-space-expansion`
**Date**: 2026-11-07

This feature does not change any public HTTP contract. The catalogue response envelope,
the `sort` parameter, and the signal endpoint remain exactly as defined in
`specs/005-related-plans-sort/contracts/recommendations-api.md`. The contract below is
internal to the backend and is consumed only by `apps.recommendations` services.

## Cache Keys

| Key | Type | Purpose |
|---|---|---|
| `recommendations:space:v1:<version>` | serialized bundle | One fitted space per corpus/configuration version. |
| `recommendations:space:active` | string | The bundle key currently served to readers. |
| `recommendations:space:refresh:lock` | string | Mutex for refresh runs. |
| `recommendations:space:last_refresh` | ISO timestamp | Last successful refresh; drives the due check. |

## Bundle Schema

```json
{
  "version": "string",
  "space": "fitted PlanSpace object",
  "values": "2-D float array",
  "masks": "2-D float array",
  "ids": [1, 2, 3],
  "published_at": ["2026-11-07T10:00:00+00:00"],
  "semantic_dimensions": 10,
  "semantic_metadata": {
    "n_features": 1024,
    "ngram_min": 2,
    "ngram_max": 4,
    "random_state": 0,
    "fitted_components": 10,
    "component_min": [0.0],
    "component_max": [1.0]
  }
}
```

## Read Contract

`PlanSpaceProvider.load(records)` MUST:

1. Map records to features, including the plan title.
2. Compute the corpus version fingerprint.
3. Resolve `recommendations:space:active`; if it points at a bundle whose `version`
   matches the fingerprint, return that bundle.
4. Otherwise fit a new space, validate it, write the versioned bundle, update the active
   pointer, and return the bundle.

Readers MUST never return a bundle whose `values` and `masks` shapes disagree or whose
version does not match the returned data.

## Refresh Contract

`refresh_plan_space_task()` MUST:

1. Acquire `recommendations:space:refresh:lock`; if unavailable, log
   `recommendation_space_refresh_skipped` and return.
2. Read published plans through `CatalogInterface.published_plan_records()`.
3. Fit the expanded space and validate the bundle.
4. Write the versioned bundle.
5. Update `recommendations:space:active` and `recommendations:space:last_refresh`.
6. Release the lock in a `finally` block.

On any failure it MUST log `recommendation_space_refresh_failed` and leave the active
pointer and `last_refresh` unchanged.

## Management Command

```text
python manage.py refresh_recommendation_space
```

The command MUST enqueue `refresh_plan_space_task` only when the configured interval has
elapsed since `recommendations:space:last_refresh`. It MUST be safe to invoke more often
than the interval.

## Compatibility

- No new HTTP endpoint, request field, or response field.
- No change to feature-005 sort semantics or signal semantics.
- Existing profiles whose `space_version` or vector length differs from the active space
  are reconciled to the cold-start prior on read.
