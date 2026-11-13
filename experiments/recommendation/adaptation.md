# E-commerce → Recommendation Space Adaptation

This document records every mapping decision used by
`experiments/recommendation/adapters/ecommerce.py`. The adapter is the only
module that knows the store's column names; the replay harness and the
recommendation services only see neutral records and interaction events.

## Product ← Plan

The model's `PlanFeatureMapper` expects plan-shaped keys. Each product row is
mapped as follows:

| Store attribute | Model slot | Type | Missing handling |
|---|---|---|---|
| `product_id` | `id` | opaque id | never missing |
| `date_added` | `published_at` | timestamp | empty string |
| `product_name` + `subcategory` + `category` + `brand` | `plan_name` (semantic title) | text | empty text |
| `price` | `price_amount` | numeric | `None` → masked |
| `rating_avg` | `cpu` | numeric | `None` → masked |
| `review_count` | `ram` | numeric | `None` → masked |
| `stock_quantity` | `disk` | numeric | `None` → masked |
| `days_since(date_added)` | `traffic` | numeric | `None` → masked |
| `category` | `location` | categorical | `None` → masked |
| `brand` | `os` | categorical | `None` → masked |

The numeric slots are the model's existing dimensions. They are reused as
price/quality proxies:

- `cpu` = rating (quality signal),
- `ram` = review count (social proof),
- `disk` = stock quantity (availability),
- `traffic` = catalogue age.

Missing values are passed as `None`, so `PlanSpace` emits a `0` mask for that
dimension. No mean/median imputation is performed.

## Interaction ← Vector + Weight

Every event is converted to the product's row vector and mask in the fitted
space. The weight is the Kalman measurement noise: **lower weight means a
stronger update**.

| Store interaction | Model weight | Rationale |
|---|---:|---|
| `view` | 0.80 | weak intent |
| `click` | 0.50 | stronger than a view |
| `add_to_wishlist` | 0.35 | explicit interest |
| `add_to_cart` | 0.30 | strong purchase intent |
| `purchase` | 0.20 | strongest observed signal |
| `remove_from_wishlist` | 1.00 | negative signal, excluded by default |
| `remove_from_cart` | 1.00 | negative signal, excluded by default |

`purchase` events come from `purchases.csv` and are merged into the user's
timeline at `order_date`. The adapter's `InteractionEvent.sign` marks
`remove_*` events as negative, but the public `RecordService` interface has no
negative-sign parameter, so the replay excludes them by default. This is a
documented limitation, not a model change.

## User ← owner_id

The store's `user_id` is used directly as the recommendation `owner_id`. The
dataset also has `session_id`, but interactions already carry `user_id`; each
user is therefore one owner, not one visitor per session. Sessions are not
merged or split for this experiment.

## Temporal Ordering

Events are sorted by `(timestamp, interaction_id)` with a stable sort. Purchase
events use `(order_date, "purchase:" + purchase_id)`. The interaction id is the
tie-breaker, so replaying the same user twice produces the same order.

All timestamps are normalized to timezone-aware UTC. This matters because the
node store persists `last_updated_at` as UTC; a naive timestamp would raise on
the Kalman decay subtraction. The adapter also forwards each event's
`occurred_at` and `interaction_id` into `RecordService`, so:

- decay is computed from the real elapsed time between interactions, not from
  wall-clock time at replay; and
- retries with the same `interaction_id` are deduplicated by the service.

## Replay Semantics

- The replay starts every sampled owner from zero nodes: the harness deletes
  that owner's persisted profile before the first event.
- Hit@N uses a lookahead horizon of 3 interactions by default (`--horizon`).
  A step is a hit when any of the next 3 interacted items appears in the top-N.
  The rank metric still uses the immediately next item.
- A "genuine interest shift" is detected as a change in the trailing
  5-interaction dominant group, not a single adjacent-category blip. The
  documented adaptation bound is 5 interactions: the top-N is considered
  adapted when at least 50% of it belongs to the new dominant group.
- Node ordinals (`node_index`) are emitted instead of the model's random
  `node_id`, so output is byte-identical across runs. The model's node ids
  remain internal to the services.

## Intent Patterns

The existing pattern registry is reused unchanged:
`cheap`, `value`, `spec_heavy`, `premium`, plus the `exploring` fallback. On
e-commerce data these read as price/quality archetypes: cheap = low price,
value = high rating/reviews relative to price, spec-heavy = high quality/social
proof, premium = high price and high quality. No new patterns are added.

## Known Limitations

1. Negative `remove_*` events are excluded because `RecordService` does not
   expose a negative-sign channel.
2. The model's dimensions are fixed hosting-plan slots; the mapping is a
   semantic proxy, not a native e-commerce embedding.
3. `rating_avg` is missing for roughly half the catalogue; those products are
   compared only on the dimensions they declare.
4. The configured production thresholds were used as-is. Any threshold
   sensitivity is reported as a finding in `report.md`, not tuned away.
5. The running `RECOMMENDATION_PATTERN_THRESHOLDS` value is
   `{cheap: 4, value: 4, spec_heavy: 4, premium: 4}` (a pre-existing deployment
   setting), not the `30` module default. The experiment did not change it.
