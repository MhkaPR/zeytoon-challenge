"""Sequential trajectory-following replay on the e-commerce dataset.

Run from the repository root:

    python experiments/recommendation/replay.py --users 20 --max-steps 40

The harness only uses the recommendation services' public interfaces. All
store-specific field names live in ``adapters/ecommerce.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid as uuidlib
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend" / "src"))

(HERE / ".cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{HERE / '.cache' / 'replay.sqlite3'}"
)

warnings.filterwarnings("ignore")

import django

django.setup()

from django.core.management import call_command

from apps.recommendations import conf
from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.explain import ExplainService
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.intent_patterns import (
    INTENT_PATTERNS,
    REAL_PATTERN_KEYS,
    build_intent_features,
)
from apps.recommendations.services.v1.nodes import NodeRepository
from apps.recommendations.services.v1.rank import RankService
from apps.recommendations.services.v1.record import Interaction, RecordService
from apps.recommendations.services.v1.space import PlanSpace
from experiments.recommendation.adapters.ecommerce import EcommerceAdapter


class StaticSpaceProvider:
    """Returns a pre-fitted bundle without touching the persisted space."""

    def __init__(self, bundle):
        self.bundle = bundle

    def load(self, records):
        return self.bundle


def reset_owner(owner_id):
    """Delete any persisted state so every replay starts from zero nodes."""
    try:
        visitor = uuidlib.UUID(str(owner_id))
    except (ValueError, AttributeError, TypeError):
        visitor = None
    if visitor is not None:
        InterestProfile.objects.filter(visitor_id=visitor).delete()
    else:
        InterestProfile.objects.filter(user_id=owner_id).delete()


def build_bundle(records):
    features = [PlanFeatureMapper().map(record) for record in records]
    space = PlanSpace(n_bins=conf.n_bins()).fit(features)
    values, masks = space.transform(features)
    return {
        "version": space.version(features),
        "space": space,
        "values": values,
        "masks": masks,
        "ids": [record["id"] for record in records],
        "published_at": [record["published_at"] for record in records],
        "raw": {},
    }


def build_patterns(bundle):
    features = build_intent_features(bundle)
    by_id = dict(zip(bundle["ids"], features))
    patterns = [
        (
            key,
            lambda plan, key=key: INTENT_PATTERNS[key].matches(plan.features),
        )
        for key in REAL_PATTERN_KEYS
    ]
    return patterns, by_id


def attach_features(ranked, by_id):
    for interest in ranked:
        for plan in interest.plans:
            plan.features = by_id.get(plan.plan_id)
    return ranked


def surfaced_intent(ranked, patterns, thresholds):
    matched = ExplainService.explain(ranked, patterns, thresholds)
    if not matched:
        return "exploring", {}
    order = {key: index for index, key in enumerate(REAL_PATTERN_KEYS)}
    key = sorted(
        matched,
        key=lambda name: (-len(matched[name]), order.get(name, 999)),
    )[0]
    counts = {name: len(plans) for name, plans in matched.items()}
    return key, counts


def merged_ranking(ranked):
    plans = {}
    for interest in ranked:
        for plan in interest.plans:
            plans.setdefault(plan.plan_id, plan)
    return sorted(plans.values(), key=lambda plan: (plan.distance, plan.plan_id))


def top_n(ranking, n, seen):
    seen = set(seen)
    ordered = [plan.plan_id for plan in ranking if plan.plan_id not in seen]
    return ordered[:n], ordered


def popularity_order(bundle, counts):
    return sorted(
        bundle["ids"],
        key=lambda item_id: (-int(counts.get(item_id, 0)), item_id),
    )


def baseline_top_n(order, n, seen):
    seen = set(seen)
    eligible = [item_id for item_id in order if item_id not in seen]
    return eligible[:n]


def replay_user(
    user_id,
    adapter,
    bundle,
    provider,
    records,
    row_of,
    patterns,
    by_id,
    popularity,
    top_n_size,
    max_steps,
    horizon,
):
    reset_owner(user_id)
    events = adapter.interactions_for_user(user_id)
    if max_steps:
        events = events[:max_steps]
    recorder = RecordService()
    ranker = RankService()
    node_repo = NodeRepository()
    thresholds = conf.pattern_thresholds()
    rank_threshold = conf.rank_threshold()
    seen: list[str] = []
    rows = []

    for index, event in enumerate(events):
        vector = adapter.to_vector(event, bundle, row_of)
        if vector is None:
            continue
        values, mask = vector
        recorder.record(
            user_id,
            Interaction(
                vector=values,
                weight=event.weight,
                kind=event.kind,
                occurred_at=event.timestamp,
                interaction_id=event.interaction_id,
                mask=mask,
                plan_ids=[event.item_id],
                space_version=bundle["version"],
            ),
            provider,
            allow_new_nodes=True,
        )
        ranked = ranker.rank(user_id, provider, records, rank_threshold)
        attach_features(ranked, by_id)
        intent, matches = surfaced_intent(ranked, patterns, thresholds)
        ranking = merged_ranking(ranked)
        model_top, model_order = top_n(ranking, top_n_size, seen)
        baseline_top = baseline_top_n(popularity, top_n_size, seen)
        nodes = node_repo.list_nodes(user_id)

        next_item = events[index + 1].item_id if index + 1 < len(events) else None
        window_items = [
            events[offset].item_id
            for offset in range(index + 1, min(index + 1 + horizon, len(events)))
        ]
        hit = None if not window_items else any(
            item in model_top for item in window_items
        )
        baseline_hit = None if not window_items else any(
            item in baseline_top for item in window_items
        )
        rank = (
            None
            if next_item is None or next_item not in model_order
            else model_order.index(next_item) + 1
        )
        baseline_rank = (
            None
            if next_item is None or next_item not in popularity
            else popularity.index(next_item) + 1
        )
        remaining = max(len(bundle["ids"]) - len(seen), 1)
        random_baseline = min(1.0, horizon * top_n_size / remaining)

        rows.append(
            {
                "user_id": user_id,
                "step": index,
                "interaction_id": event.interaction_id,
                "kind": event.kind,
                "group": adapter.group_of(event.item_id),
                "item_id": event.item_id,
                "next_item_id": next_item,
                "next_group": (
                    adapter.group_of(next_item)
                    if next_item is not None
                    else None
                ),
                "top_n": model_top,
                "top_n_groups": [
                    adapter.group_of(item) for item in model_top
                ],
                "hit_window": window_items,
                "hit": hit,
                "rank": rank,
                "baseline_top_n": baseline_top,
                "baseline_hit": baseline_hit,
                "baseline_rank": baseline_rank,
                "random_baseline": random_baseline,
                "intent": intent,
                "intent_match_counts": matches,
                "node_count": len(nodes),
                "nodes": [
                    {
                        "node_index": position,
                        "position": [float(value) for value in node.position],
                        "signal_count": int(node.signal_count),
                    }
                    for position, node in enumerate(nodes)
                ],
            }
        )
        seen.append(event.item_id)
    return rows


def summarise_user(user_id, rows, top_n_size):
    scored = [row for row in rows if row["hit"] is not None]
    hits = np.asarray([float(row["hit"]) for row in scored]) if scored else np.array([])
    baseline = (
        np.asarray([float(row["baseline_hit"]) for row in scored])
        if scored
        else np.array([])
    )
    intents = [row["intent"] for row in rows]
    changes = sum(
        1 for previous, current in zip(intents, intents[1:]) if previous != current
    )
    random_baseline = (
        float(np.mean([row["random_baseline"] for row in scored]))
        if scored
        else 0.0
    )
    recovery = None
    window = 5
    for index in range(len(hits)):
        if index + 1 < window:
            continue
        if float(np.mean(hits[index + 1 - window : index + 1])) > random_baseline:
            recovery = index + 1
            break
    groups_seq = [row["group"] for row in rows]
    dominant_seq = _rolling_dominant(groups_seq, window=5)
    shifts = [
        index
        for index in range(1, len(dominant_seq))
        if dominant_seq[index] is not None
        and dominant_seq[index] != dominant_seq[index - 1]
    ]
    adaptation = []
    for index in shifts:
        target = dominant_seq[index]
        for offset in range(index, len(rows)):
            groups = [group for group in rows[offset]["top_n_groups"] if group]
            if groups and groups.count(target) / len(groups) >= 0.5:
                adaptation.append(offset - index)
                break
    alignment = [
        (
            sum(
                1
                for group in row["top_n_groups"]
                if group == dominant_seq[index]
            )
            / max(len(row["top_n_groups"]), 1)
        )
        for index, row in enumerate(rows)
        if row["top_n_groups"] and dominant_seq[index] is not None
    ]
    overall = Counter(group for group in groups_seq if group)
    dominant_group_share = (
        overall.most_common(1)[0][1] / max(len(groups_seq), 1) if overall else 0.0
    )
    return {
        "user_id": user_id,
        "steps": len(rows),
        "scored_steps": len(scored),
        f"hit@{top_n_size}": float(hits.mean()) if hits.size else 0.0,
        f"baseline_hit@{top_n_size}": float(baseline.mean()) if baseline.size else 0.0,
        "median_rank": (
            float(np.median([row["rank"] for row in scored if row["rank"] is not None]))
            if any(row["rank"] is not None for row in scored)
            else None
        ),
        "intent_changes": changes,
        "final_nodes": rows[-1]["node_count"] if rows else 0,
        "max_nodes": max((row["node_count"] for row in rows), default=0),
        "cold_start_recovery_step": recovery,
        "random_baseline": random_baseline,
        "group_shifts": len(shifts),
        "median_steps_to_align": (
            float(np.median(adaptation)) if adaptation else None
        ),
        "align_within_5": sum(1 for value in adaptation if value <= 5),
        "shifts_never_aligned": len(shifts) - len(adaptation),
        "mean_top_n_alignment": (
            float(np.mean(alignment)) if alignment else 0.0
        ),
        "nodes_per_step": (
            (rows[-1]["node_count"] / len(rows)) if rows else 0.0
        ),
        "dominant_group_share": float(dominant_group_share),
    }


def _rolling_dominant(groups, window=5):
    """Sustained dominant group over a trailing window (deterministic ties)."""
    result = []
    for index in range(len(groups)):
        chunk = [g for g in groups[max(0, index + 1 - window) : index + 1] if g]
        if not chunk:
            result.append(None)
            continue
        counts = Counter(chunk)
        best = max(counts.items(), key=lambda item: (item[1], -chunk.index(item[0])))
        result.append(best[0])
    return result


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--min-interactions", type=int, default=10)
    parser.add_argument("--max-interactions", type=int, default=60)
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-dir", default=str(HERE / "output"))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args(argv)

    call_command("migrate", verbosity=0, interactive=False)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    adapter = EcommerceAdapter()
    records = adapter.product_records()
    bundle = build_bundle(records)
    provider = StaticSpaceProvider(bundle)
    row_of = {item_id: index for index, item_id in enumerate(bundle["ids"])}
    patterns, by_id = build_patterns(bundle)
    popularity = popularity_order(bundle, adapter.popularity_counts())
    users = adapter.sample_users(
        args.users,
        min_interactions=args.min_interactions,
        max_interactions=args.max_interactions,
        seed=args.seed,
    )

    all_rows = []
    summaries = []
    for user_id in users:
        rows = replay_user(
            user_id,
            adapter,
            bundle,
            provider,
            records,
            row_of,
            patterns,
            by_id,
            popularity,
            args.top_n,
            args.max_steps,
            args.horizon,
        )
        all_rows.extend(rows)
        summaries.append(summarise_user(user_id, rows, args.top_n))

    jsonl_path = output_dir / "replay.jsonl"
    write_jsonl(jsonl_path, all_rows)
    digest = sha256(jsonl_path)

    summary = {
        "config": {
            "users": len(users),
            "top_n": args.top_n,
            "horizon": args.horizon,
            "max_steps": args.max_steps,
            "seed": args.seed,
            "rank_threshold": conf.rank_threshold(),
            "pattern_thresholds": conf.pattern_thresholds(),
            "space_version": bundle["version"],
        },
        "users": summaries,
        "jsonl_sha256": digest,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    try:
        import pandas as pd

        frame = pd.DataFrame(summaries)
        frame.to_csv(output_dir / "metrics.csv", index=False)
    except Exception:
        pass

    if not args.no_plots:
        from experiments.recommendation import report

        report.build_plots(
            all_rows,
            summaries,
            bundle,
            adapter,
            HERE / "plots",
            args.top_n,
        )
        report.build_report(
            summary,
            all_rows,
            summaries,
            bundle,
            adapter,
            output_dir,
            HERE / "report.md",
            args.top_n,
        )

    print(f"users={len(users)} steps={len(all_rows)} sha256={digest}")
    print(f"output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
