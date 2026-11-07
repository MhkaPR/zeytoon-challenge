# Quickstart Validation: Periodic PCA Space Expansion

**Feature**: `006-pca-space-expansion`
**Date**: 2026-11-07

## Prerequisites

- Python dependencies installed with `uv sync` (includes the new `scikit-learn`).
- PostgreSQL and Redis available for a manual run; tests use locmem cache.
- At least a few published plans with `values.plan_name` set.

## Automated Checks

```bash
uv run pytest backend/src/apps/recommendations/tests backend/src/apps/catalog/tests -q
```

Expected: all tests pass, including the new semantic, store, task, and ranking tests.

## Scenario 1 — Expanded space has ten semantic dimensions

```bash
uv run python backend/src/manage.py shell -c "
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.services.v1.store import PlanSpaceProvider
bundle = PlanSpaceProvider().load(CatalogInterface.published_plan_records())
print(bundle['version'])
print(bundle['semantic_dimensions'])
print(bundle['values'].shape, bundle['masks'].shape)
print(bundle['space'].names[-10:])
"
```

Expected: `semantic_dimensions` is `10`; the last ten names are `semantic_0` through
`semantic_9`; the value and mask shapes match.

## Scenario 2 — Periodic refresh publishes a new space

```bash
uv run python backend/src/manage.py refresh_recommendation_space
uv run python backend/src/manage.py shell -c "
from django.core.cache import cache
print(cache.get('recommendations:space:active'))
print(cache.get('recommendations:space:last_refresh'))
"
```

Expected: the command enqueues the refresh when due; the active key and last-refresh
timestamp are present. Running the command again before the interval elapses skips the
enqueue.

## Scenario 3 — Cold start stays deterministic

```bash
uv run python backend/src/manage.py shell -c "
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.services.v1.store import PlanSpaceProvider
records = CatalogInterface.published_plan_records()
first = PlanSpaceProvider().load(records)
second = PlanSpaceProvider().load(records)
print(first['version'] == second['version'])
print((first['values'] == second['values']).all())
"
```

Expected: both lines print `True`.

## Scenario 4 — Outdated profile is reconciled

```bash
uv run python backend/src/manage.py shell -c "
import uuid
from apps.recommendations.models import InterestProfile
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.services.v1.ranking import RankingService
records = CatalogInterface.published_plan_records()
visitor = uuid.uuid4()
InterestProfile.objects.create(visitor_id=visitor, position=[0.0], uncertainty=[0.1], space_version='old')
ordered = RankingService().rank(records, [r['id'] for r in records], visitor_id=visitor)
print(len(ordered))
"
```

Expected: the ranking request succeeds and returns the candidate ids without raising.

## Scenario 5 — Failed refresh keeps the previous space

1. Record the active bundle key.
2. Force the refresh to fail (for example by temporarily raising inside the fit step in
   a local shell or test).
3. Reload the catalogue.

Expected: the active key is unchanged, catalogue ordering is unchanged, and a
`recommendation_space_refresh_failed` log entry is emitted.

## Scenario 6 — No public contract regression

```bash
uv run pytest backend/src/apps/catalog/tests/test_related_sort.py -q
```

Expected: default related ordering, price sorts, pagination, and signal-driven ordering
continue to pass exactly as in feature 005.
