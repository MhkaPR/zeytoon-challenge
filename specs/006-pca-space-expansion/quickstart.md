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

## 5. Confirm multiple interests are kept

```bash
uv run python backend/src/manage.py shell -c "
import uuid
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.models import InterestProfile
records = CatalogInterface.published_plan_records()
by_title = {r['values'].get('plan_name'): r['id'] for r in records}
picks = [by_title[t] for t in ('python10', 'هاست nodejs 1', 'Email10') if t in by_title]
v = uuid.uuid4()
for plan_id in picks:
    SignalRecorder().record(records, 'destination_visit', [plan_id], visitor_id=v)
print(len(InterestProfile.objects.get(visitor_id=v).position))
"
```

Expected: `3` clusters when the sample plans exist, so python, node, and email stay
represented.

## 6. Rebuild clusters from historical signals

```bash
uv run python backend/src/manage.py rebuild_interest_clusters --visitor-id <visitor-uuid>
```

Expected: the profile is replayed from its recorded signals and prints one line with the
resulting cluster count. Use `--dry-run` to inspect without saving.
