# Quickstart Validation: Periodic PCA Space Expansion

## 1. Run tests

```bash
uv run pytest backend/src/apps/recommendations/tests backend/src/apps/catalog/tests -q
```

Expected: all pass.

## 2. Check the expanded space

```bash
uv run python backend/src/manage.py shell -c "
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.services.v1.store import PlanSpaceProvider
b = PlanSpaceProvider().load(CatalogInterface.published_plan_records())
print(b['values'].shape, b['masks'].shape)
print(b['space'].names[-10:])
"
```

Expected: ten `semantic_0` … `semantic_9` names and matching shapes.

## 3. Run the scheduled refresh

```bash
uv run python backend/src/manage.py refresh_recommendation_space
```

Expected: the refresh task is enqueued; the space is cached under its version key.

## 4. Confirm outdated profiles still work

```bash
uv run python backend/src/manage.py shell -c "
import uuid
from apps.recommendations.models import InterestProfile
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.services.v1.ranking import RankingService
records = CatalogInterface.published_plan_records()
v = uuid.uuid4()
InterestProfile.objects.create(visitor_id=v, position=[0.0], uncertainty=[0.1], space_version='old')
print(len(RankingService().rank(records, [r['id'] for r in records], visitor_id=v)))
"
```

Expected: no error; candidate ids are returned.
