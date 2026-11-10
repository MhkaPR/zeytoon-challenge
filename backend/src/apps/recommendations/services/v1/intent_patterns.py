"""Intent patterns for recommendation explanations.

Patterns are predicates over the normalized plan space. Adding a pattern means adding
one entry to ``INTENT_PATTERNS``; the scoring code never needs an if/elif branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from apps.recommendations import conf


@dataclass(frozen=True)
class PlanIntentFeatures:
    """Normalized feature view used by every intent predicate."""

    price_pct: float | None = None
    cpu_pct: float | None = None
    ram_pct: float | None = None
    disk_pct: float | None = None
    spec_pct: float | None = None


@dataclass(frozen=True)
class IntentPattern:
    """One named intent predicate."""

    key: str
    predicate: Callable[[PlanIntentFeatures], bool]
    fallback: bool

    def matches(self, features: PlanIntentFeatures) -> bool:
        return self.predicate(features)


def _mean(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _dimension_index(names: list[str], field: str) -> int | None:
    try:
        return names.index(field)
    except ValueError:
        return None


def build_intent_features(bundle) -> list[PlanIntentFeatures]:
    """Build one normalized feature view per catalog row in the loaded bundle."""
    names = list(bundle["space"].names)
    values = bundle["values"]
    masks = bundle["masks"]
    indices = {
        field: _dimension_index(names, field)
        for field in ("price", "cpu", "ram", "disk")
    }
    features: list[PlanIntentFeatures] = []
    for row in range(values.shape[0]):
        def value_of(field: str) -> float | None:
            index = indices[field]
            if index is None or masks[row][index] <= 0:
                return None
            return float(values[row][index])

        price = value_of("price")
        cpu = value_of("cpu")
        ram = value_of("ram")
        disk = value_of("disk")
        features.append(
            PlanIntentFeatures(
                price_pct=price,
                cpu_pct=cpu,
                ram_pct=ram,
                disk_pct=disk,
                spec_pct=_mean([ram, cpu, disk]),
            )
        )
    return features


def _cheap(features: PlanIntentFeatures) -> bool:
    return features.price_pct is not None and features.price_pct < 0.30


def _value(features: PlanIntentFeatures) -> bool:
    if features.price_pct is None or features.spec_pct is None:
        return False
    return features.spec_pct - features.price_pct > 0.15


def _spec_heavy(features: PlanIntentFeatures) -> bool:
    return features.spec_pct is not None and features.spec_pct > 0.70


def _premium(features: PlanIntentFeatures) -> bool:
    if features.price_pct is None or features.spec_pct is None:
        return False
    return features.price_pct > 0.70 and features.spec_pct > 0.70


def _always(_: PlanIntentFeatures) -> bool:
    return True


INTENT_PATTERNS: dict[str, IntentPattern] = {
    "cheap": IntentPattern(
        key="cheap",
        predicate=_cheap,
        fallback=False,
    ),
    "value": IntentPattern(
        key="value",
        predicate=_value,
        fallback=False,
    ),
    "spec_heavy": IntentPattern(
        key="spec_heavy",
        predicate=_spec_heavy,
        fallback=False,
    ),
    "premium": IntentPattern(
        key="premium",
        predicate=_premium,
        fallback=False,
    ),
    "exploring": IntentPattern(
        key="exploring",
        predicate=_always,
        fallback=True,
    ),
}

REAL_PATTERN_KEYS: tuple[str, ...] = tuple(
    key for key, pattern in INTENT_PATTERNS.items() if not pattern.fallback
)

FALLBACK_KEY = "exploring"

def pattern_matches(key: str, features: PlanIntentFeatures) -> bool:
    return INTENT_PATTERNS[key].matches(features)


def message_for(key: str, direction: str | None = None) -> str:
    messages = conf.explain_messages().get(key, {})
    resolved = direction or "positive"
    return messages.get(resolved) or messages.get("positive") or key


__all__ = [
    "FALLBACK_KEY",
    "INTENT_PATTERNS",
    "IntentPattern",
    "PlanIntentFeatures",
    "REAL_PATTERN_KEYS",
    "build_intent_features",
    "message_for",
    "pattern_matches",
]
