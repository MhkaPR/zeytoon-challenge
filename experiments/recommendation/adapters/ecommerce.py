"""Map the e-commerce dataset onto the recommendation space.

This is the only module in the experiment that knows the store's column names.
Everything downstream (replay harness, metrics, plots) consumes the neutral
``ProductRecord`` / ``InteractionEvent`` shapes defined here.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "datasets"

# Lower weight means a stronger Kalman update (it is measurement noise).
DEFAULT_WEIGHTS = {
    "view": 0.8,
    "click": 0.5,
    "add_to_wishlist": 0.35,
    "add_to_cart": 0.3,
    "purchase": 0.2,
    "remove_from_wishlist": 1.0,
    "remove_from_cart": 1.0,
}

NEGATIVE_KINDS = {"remove_from_wishlist", "remove_from_cart"}


@dataclass(frozen=True)
class InteractionEvent:
    """One store interaction expressed in model-neutral terms."""

    interaction_id: str
    user_id: str
    item_id: str
    kind: str
    timestamp: datetime
    weight: float
    sign: int = 1


class EcommerceAdapter:
    """Loads the store CSVs and exposes plan-shaped records and events."""

    def __init__(self, data_dir=None, weights=None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)
        self._products = None
        self._interactions = None
        self._purchases = None
        self._users = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    @property
    def products(self) -> pd.DataFrame:
        if self._products is None:
            self._products = (
                pd.read_csv(self.data_dir / "products.csv")
                .drop_duplicates("product_id")
                .reset_index(drop=True)
            )
        return self._products

    @property
    def interactions(self) -> pd.DataFrame:
        if self._interactions is None:
            self._interactions = pd.read_csv(
                self.data_dir / "interactions.csv",
                parse_dates=["timestamp"],
            )
        return self._interactions

    @property
    def purchases(self) -> pd.DataFrame:
        if self._purchases is None:
            self._purchases = pd.read_csv(
                self.data_dir / "purchases.csv",
                parse_dates=["order_date"],
            )
        return self._purchases

    @property
    def users(self) -> pd.DataFrame:
        if self._users is None:
            self._users = pd.read_csv(self.data_dir / "users.csv")
        return self._users

    # ------------------------------------------------------------------
    # Product -> plan-shaped record
    # ------------------------------------------------------------------
    def product_records(self) -> list[dict]:
        return [self._record(row) for row in self.products.itertuples(index=False)]

    def product_record(self, product_id: str) -> dict | None:
        rows = self.products[self.products["product_id"] == product_id]
        if rows.empty:
            return None
        return self._record(next(rows.itertuples(index=False)))

    def group_of(self, item_id: str) -> str | None:
        """Return the product's coarse group (category) for shift analysis."""
        rows = self.products[self.products["product_id"] == item_id]
        if rows.empty:
            return None
        value = rows.iloc[0].get("category")
        return None if pd.isna(value) else str(value)

    def groups(self) -> dict[str, str]:
        return {
            str(row.product_id): str(row.category)
            for row in self.products.itertuples(index=False)
            if not pd.isna(getattr(row, "category", None))
        }

    def popularity_counts(self) -> dict[str, int]:
        """Global interaction count per item, used only for the baseline."""
        counts = self.interactions.groupby("product_id").size()
        return {str(item_id): int(count) for item_id, count in counts.items()}

    def _record(self, row) -> dict:
        """Map one product row onto the model's plan slots.

        Missing values are passed as ``None`` so the space masks the dimension
        instead of imputing it.
        """
        rating = _optional_float(getattr(row, "rating_avg", None))
        reviews = _optional_float(getattr(row, "review_count", None))
        stock = _optional_float(getattr(row, "stock_quantity", None))
        price = _optional_float(getattr(row, "price", None))
        added = getattr(row, "date_added", None)
        title = " ".join(
            str(value)
            for value in (
                getattr(row, "product_name", ""),
                getattr(row, "subcategory", ""),
                getattr(row, "category", ""),
                getattr(row, "brand", ""),
            )
            if value is not None and str(value).strip()
        )
        return {
            "id": row.product_id,
            "published_at": str(added) if added is not None else "",
            "values": {
                "plan_name": title,
                "price_amount": price,
                "cpu": rating,
                "ram": reviews,
                "disk": stock,
                "traffic": _days_since(added),
                "location": getattr(row, "category", None),
                "os": getattr(row, "brand", None),
            },
        }

    # ------------------------------------------------------------------
    # Interactions -> chronological events
    # ------------------------------------------------------------------
    def interactions_for_user(
        self,
        user_id: str,
        include_purchases: bool = True,
        include_negative: bool = False,
    ) -> list[InteractionEvent]:
        rows = self.interactions[self.interactions["user_id"] == user_id]
        events = [
            InteractionEvent(
                interaction_id=str(row.interaction_id),
                user_id=str(row.user_id),
                item_id=str(row.product_id),
                kind=str(row.interaction_type),
                timestamp=_utc(row.timestamp),
                weight=self.interaction_weight(row.interaction_type),
                sign=-1 if row.interaction_type in NEGATIVE_KINDS else 1,
            )
            for row in rows.itertuples(index=False)
        ]
        if include_purchases:
            bought = self.purchases[self.purchases["user_id"] == user_id]
            events.extend(
                InteractionEvent(
                    interaction_id=f"purchase:{row.purchase_id}",
                    user_id=str(row.user_id),
                    item_id=str(row.product_id),
                    kind="purchase",
                    timestamp=_utc(row.order_date),
                    weight=self.interaction_weight("purchase"),
                    sign=1,
                )
                for row in bought.itertuples(index=False)
            )
        if not include_negative:
            events = [event for event in events if event.sign > 0]
        events.sort(key=lambda event: (event.timestamp, event.interaction_id))
        return events

    def interaction_weight(self, kind: str) -> float:
        return float(self.weights.get(kind, 1.0))

    # ------------------------------------------------------------------
    # User sampling
    # ------------------------------------------------------------------
    def sample_users(
        self,
        count: int,
        min_interactions: int = 10,
        max_interactions: int = 80,
        seed: int = 0,
    ) -> list[str]:
        counts = self.interactions.groupby("user_id").size()
        eligible = sorted(
            user_id
            for user_id, size in counts.items()
            if min_interactions <= int(size) <= max_interactions
        )
        if count >= len(eligible):
            return eligible
        picked = random.Random(seed).sample(eligible, count)
        return sorted(picked)

    # ------------------------------------------------------------------
    # Event -> space vector
    # ------------------------------------------------------------------
    def to_vector(self, event: InteractionEvent, bundle, row_of=None):
        row_of = row_of or {
            product_id: index for index, product_id in enumerate(bundle["ids"])
        }
        row = row_of.get(event.item_id)
        if row is None:
            return None
        return (
            bundle["values"][row].tolist(),
            bundle["masks"][row].tolist(),
        )


def _optional_float(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def _days_since(value):
    if value is None or pd.isna(value):
        return None
    try:
        moment = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    return float((pd.Timestamp("2026-01-01") - moment).days)


def _utc(value):
    """Return a timezone-aware UTC datetime for stable, comparable timestamps."""
    moment = pd.Timestamp(value)
    if moment.tzinfo is None:
        moment = moment.tz_localize("UTC")
    else:
        moment = moment.tz_convert("UTC")
    return moment.to_pydatetime(warn=False)


__all__ = [
    "DEFAULT_WEIGHTS",
    "EcommerceAdapter",
    "InteractionEvent",
    "NEGATIVE_KINDS",
]
