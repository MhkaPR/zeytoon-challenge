from pathlib import Path

import numpy as np

from experiments.recommendation.adapters.ecommerce import (
    EcommerceAdapter,
    InteractionEvent,
)

HERE = Path(__file__).resolve().parents[1]


def test_product_record_maps_declared_attributes():
    adapter = EcommerceAdapter()
    records = adapter.product_records()
    assert len(records) > 0
    record = next(
        item for item in records if item["values"]["cpu"] is not None
    )
    assert record["id"]
    assert record["published_at"]
    assert record["values"]["plan_name"]
    assert record["values"]["price_amount"] is not None
    assert record["values"]["location"]
    assert record["values"]["os"]


def test_missing_attribute_is_masked_not_imputed():
    adapter = EcommerceAdapter()
    record = next(
        item
        for item in adapter.product_records()
        if item["values"]["cpu"] is None
    )
    assert record["values"]["cpu"] is None


def test_interactions_are_chronological_with_stable_tie_breaker():
    adapter = EcommerceAdapter()
    user_id = adapter.sample_users(1, min_interactions=5)[0]
    events = adapter.interactions_for_user(user_id)
    keys = [(event.timestamp, event.interaction_id) for event in events]
    assert keys == sorted(keys)
    assert all(event.timestamp.tzinfo is not None for event in events)


def test_weights_are_documented_and_configurable():
    adapter = EcommerceAdapter()
    assert adapter.interaction_weight("view") == 0.8
    assert adapter.interaction_weight("purchase") == 0.2
    custom = EcommerceAdapter(weights={"view": 0.1})
    assert custom.interaction_weight("view") == 0.1


def test_negative_events_are_excluded_by_default():
    adapter = EcommerceAdapter()
    raw = adapter.interactions
    negative_users = raw[
        raw["interaction_type"].str.startswith("remove")
    ]["user_id"].unique()
    assert len(negative_users) > 0
    user_id = str(negative_users[0])
    positive = adapter.interactions_for_user(user_id, include_negative=False)
    assert all(event.sign > 0 for event in positive)
    with_negative = adapter.interactions_for_user(
        user_id, include_negative=True
    )
    assert any(event.sign < 0 for event in with_negative)


def test_event_vector_uses_the_bundle_row():
    adapter = EcommerceAdapter()
    bundle = {
        "ids": ["a", "b"],
        "values": np.asarray([[1.0, 2.0], [3.0, 4.0]]),
        "masks": np.asarray([[1.0, 1.0], [1.0, 0.0]]),
    }
    event = InteractionEvent(
        interaction_id="x",
        user_id="u",
        item_id="b",
        kind="view",
        timestamp=None,
        weight=0.8,
    )
    values, mask = adapter.to_vector(event, bundle)
    assert values == [3.0, 4.0]
    assert mask == [1.0, 0.0]


def test_harness_does_not_know_store_field_names():
    forbidden = [
        "product_name",
        "review_count",
        "stock_quantity",
        "rating_avg",
        "interaction_type",
        "price_amount",
        "date_added",
        "subcategory",
        "category",
        "brand",
        "product_id",
    ]
    for name in ("replay.py", "report.py"):
        text = (HERE / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{name} leaks store field {token}"
