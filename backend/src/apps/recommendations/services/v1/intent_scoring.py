"""Statistical gates and ranking for intent patterns."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import fisher_exact

from apps.recommendations import conf
from apps.recommendations.services.v1.intent_patterns import REAL_PATTERN_KEYS


@dataclass(frozen=True)
class ContingencyTable:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def pattern_size(self) -> int:
        return self.tp + self.fp

    @property
    def candidate_size(self) -> int:
        return self.tp + self.fn

    @property
    def catalog_size(self) -> int:
        return self.tp + self.fp + self.fn + self.tn


@dataclass(frozen=True)
class IntentScore:
    key: str
    lift: float
    p_value: float
    mcc: float
    score: float
    direction: str

    def confidence(self) -> dict[str, float]:
        return {
            "lift": round(float(self.lift), 6),
            "p": round(float(self.p_value), 6),
            "mcc": round(float(self.mcc), 6),
        }


def contingency_table(
    candidate_rows: set[int],
    pattern_rows: set[int],
    catalog_size: int,
) -> ContingencyTable:
    tp = len(candidate_rows & pattern_rows)
    fp = len(pattern_rows) - tp
    fn = len(candidate_rows) - tp
    tn = catalog_size - len(candidate_rows) - fp
    return ContingencyTable(tp=tp, fp=fp, fn=fn, tn=max(tn, 0))


def fisher_p_value(table: ContingencyTable) -> float:
    _, p_value = fisher_exact(
        [[table.tp, table.fp], [table.fn, table.tn]],
        alternative="two-sided",
    )
    return float(p_value)


def lift(table: ContingencyTable) -> float:
    if (
        table.pattern_size <= 0
        or table.candidate_size <= 0
        or table.catalog_size <= 0
    ):
        return 0.0
    baseline = table.candidate_size / table.catalog_size
    if baseline <= 0:
        return 0.0
    return (table.tp / table.pattern_size) / baseline


def matthews_correlation(tp: int, tn: int, fp: int, fn: int) -> float:
    numerator = tp * tn - fp * fn
    denominator = math.sqrt(
        (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    )
    if denominator == 0:
        return 0.0
    return numerator / denominator


def evaluate_pattern(key: str, table: ContingencyTable) -> IntentScore | None:
    if table.pattern_size < conf.explain_min_pattern_size():
        return None
    p_value = fisher_p_value(table)
    if p_value > conf.explain_alpha():
        return None
    lift_value = lift(table)
    if lift_value < conf.explain_min_lift():
        return None
    mcc = matthews_correlation(table.tp, table.tn, table.fp, table.fn)
    if abs(mcc) < conf.explain_min_mcc():
        return None
    return IntentScore(
        key=key,
        lift=lift_value,
        p_value=p_value,
        mcc=mcc,
        score=lift_value * abs(mcc),
        direction="positive" if mcc > 0 else "negative",
    )


def evaluate_patterns(
    candidate_rows: set[int],
    pattern_rows_by_key: dict[str, set[int]],
    catalog_size: int,
) -> list[IntentScore]:
    scores: list[IntentScore] = []
    for key in REAL_PATTERN_KEYS:
        table = contingency_table(
            candidate_rows,
            pattern_rows_by_key.get(key, set()),
            catalog_size,
        )
        score = evaluate_pattern(key, table)
        if score is not None:
            scores.append(score)
    return scores


def best_score(scores: list[IntentScore]) -> IntentScore | None:
    if not scores:
        return None
    order = {key: index for index, key in enumerate(REAL_PATTERN_KEYS)}
    return sorted(scores, key=lambda item: (-item.score, order.get(item.key, 999)))[0]


__all__ = [
    "ContingencyTable",
    "IntentScore",
    "best_score",
    "contingency_table",
    "evaluate_pattern",
    "evaluate_patterns",
    "fisher_p_value",
    "lift",
    "matthews_correlation",
]
