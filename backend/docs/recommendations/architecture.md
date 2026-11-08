# recommendations — Architecture

## 1. Responsibility

`apps.recommendations` orders plans for a viewer and records interest signals. It owns:

- anonymous (`visitor_id`) and account (`user`) interest profiles;
- append-only interest signals;
- a cached, versioned plan space;
- Kalman-style preference updates and multi-interest clusters;
- related-plan ranking used by the catalog;
- visitor-profile merge on login and cleanup on logout;
- scheduled plan-space refresh.

It is a pure ranking service: it does not publish or edit plans.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `models/interest_profile.py` | `InterestProfile` |
| `models/interest_signal.py` | `InterestSignal` |
| `services/v1/features.py` | map published plan values to features |
| `services/v1/space.py` | numeric binning, categorical one-hot, semantic PCA |
| `services/v1/semantic.py` | title hashing + PCA semantic components |
| `services/v1/store.py` | fit/cache/refresh the plan space |
| `services/v1/state.py` | `UserState`, `InterestClusters` |
| `services/v1/recommender.py` | masked distance and deterministic ordering |
| `services/v1/ranking.py` | `RankingService` facade |
| `services/v1/signals.py` | `SignalRecorder` |
| `services/v1/merging.py` | `StateMerger` |
| `interfaces.py` | `RecommendationsInterface` |
| `views/v1/signals.py` | signal endpoint |
| `tasks.py` | scheduled space refresh |
| `management/commands/*` | refresh space, rebuild clusters |
| `conf.py` | constance-backed tunables |

## 3. Plan space

Each plan becomes a point in `[0,1]^d` with a per-dimension mask:

- numeric: `price`, `cpu`, `ram`, `disk`, `traffic` (quantile bins);
- presence flags for resources and categories;
- categorical one-hot: `country`, `os`;
- semantic components: hashed character n-grams of the plan title reduced by PCA.

Plans are compared only on dimensions they declare (`mask=1`).

## 4. Interest state

`UserState` holds a position and per-dimension uncertainty. `update()`:

```text
uncertainty += drift
gain = uncertainty / (uncertainty + noise)
position += sign * gain * (observed - position)
uncertainty = (1 - gain) * uncertainty
```

Positive signals use `sign=+1`; negative signals use `-negative_factor`.

`InterestClusters` keeps up to `RECOMMENDATION_MAX_INTEREST_CLUSTERS` positions. A signal
updates the nearest cluster when its distance is within
`RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD`; otherwise it starts a new cluster.

## 5. Cold start

When a viewer has no profile (or a profile from an older space version),
`InterestClusters.from_profile()` uses the plan-space prior: the masked mean of all plans.
Ordering is therefore deterministic for anonymous first-time visitors.

## 6. Caching

The fitted space is cached under `recommendations:space:v1:{version}`. The version hashes
the latest publish timestamp, plan count, plan ids/titles, and semantic configuration.
A failed refresh leaves the previous cache key intact.

## 7. Dependencies

- `apps.catalog.interfaces` for published plan records.
- `apps.utils.models.TimestampedModel`.
- `django.core.cache` for the space cache and per-viewer signal caps.
- `numpy` / `scikit-learn` for the space and semantic encoder.
