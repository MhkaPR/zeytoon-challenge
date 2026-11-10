#!/usr/bin/env python
"""Read-only proof of the recommender on the REAL published catalog.

Unlike ``generate_recommendation_proof.py`` (which uses an isolated synthetic
catalog), this script reads the developer's published plans and builds the
recommendation space purely in memory. It never writes profiles, signals,
spaces, or catalog rows.

It selects plans by their real normalized percentiles, builds in-memory interest
states, and asks the real ``IntentExplainer`` for explanations. The JSON/HTML
artifacts include the statistical gate diagnostics for every intent pattern, so
a rejected intent can be explained instead of hidden.

Run from the repository root::

    .venv/bin/python backend/scripts/generate_real_catalog_proof.py
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
OUTPUT_DIR = (
    REPO_ROOT
    / "specs"
    / "008-intent-pattern-explanations"
    / "artifacts"
)

sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django  # noqa: E402

django.setup()

import numpy as np  # noqa: E402

from apps.catalog.interfaces import CatalogInterface  # noqa: E402
from apps.recommendations import conf  # noqa: E402
from apps.recommendations.services.v1.eligibility import eligible_rows  # noqa: E402
from apps.recommendations.services.v1.explanation import IntentExplainer  # noqa: E402
from apps.recommendations.services.v1.features import PlanFeatureMapper  # noqa: E402
from apps.recommendations.services.v1.intent_scoring import (  # noqa: E402
    contingency_table,
    fisher_p_value,
    lift,
    matthews_correlation,
)
from apps.recommendations.services.v1.recommender import Recommender  # noqa: E402
from apps.recommendations.services.v1.space import PlanSpace  # noqa: E402
from apps.recommendations.services.v1.state import (  # noqa: E402
    InterestClusters,
    UserState,
)


def _records():
    return CatalogInterface.published_plan_records()


def _bundle(records):
    features = [PlanFeatureMapper().map(record) for record in records]
    space = PlanSpace(n_bins=conf.n_bins()).fit(features)
    values, masks = space.transform(features)
    return {
        "version": space.version(features),
        "space": space,
        "values": values,
        "masks": masks,
        "ids": [feature["id"] for feature in features],
        "published_at": [feature["published_at"] for feature in features],
    }


def _summary(record):
    values = record.get("values") or {}
    return {
        "id": record.get("id"),
        "name": values.get("plan_name") or values.get("title") or values.get("name"),
        "plan_type": values.get("plan_type"),
        "price": values.get("price_amount", values.get("price")),
        "cpu": values.get("vcpu_cores", values.get("cpu_cores", values.get("cpu"))),
        "ram": values.get("ram_amount", values.get("ram")),
        "disk": values.get("disk_amount", values.get("disk")),
    }


def _state_from_rows(values, masks, rows, kind):
    noise = conf.signal_noise(kind)
    if kind == "search_impression":
        centroid = values[rows].mean(axis=0)
        mask = masks[rows].max(axis=0)
        state = UserState(centroid, mask)
        state.update(centroid, mask, noise)
    else:
        state = UserState(values[rows[0]], masks[rows[0]])
        for row in rows[1:]:
            state.update(values[row], masks[row], noise)
    state.activity = float(len(rows))
    return state


def _clusters(states):
    return InterestClusters(
        [state.x for state in states],
        [state.s for state in states],
        [state.activity for state in states],
    )


def _signals(records, groups, kind):
    return [
        SimpleNamespace(kind=kind, plan_ids=[records[row]["id"] for row in rows])
        for rows in groups
    ]


def _diagnostics(explainer, position, click_rows):
    distances = Recommender.distances(
        explainer.values, explainer.masks, position
    )
    distances = np.where(explainer.eligible, distances, np.inf)
    ordered = Recommender.order(
        explainer.ids, distances, explainer.published_at
    )
    row_of = {plan_id: index for index, plan_id in enumerate(explainer.ids)}
    limit = max(conf.explain_k(), 1)
    candidates = [
        row_of[plan_id]
        for plan_id in ordered
        if explainer.eligible[row_of[plan_id]]
    ][:limit]
    candidate_rows = set(candidates)
    results = []
    min_size = conf.explain_min_pattern_size()
    alpha = conf.explain_alpha()
    min_lift = conf.explain_min_lift()
    min_mcc = conf.explain_min_mcc()
    for key in ("cheap", "value", "spec_heavy", "premium"):
        table = contingency_table(
            candidate_rows, explainer.pattern_rows[key], explainer.total
        )
        p_value = fisher_p_value(table)
        lift_value = lift(table)
        mcc = matthews_correlation(table.tp, table.tn, table.fp, table.fn)
        reasons = []
        if table.pattern_size < min_size:
            reasons.append(f"pattern_size {table.pattern_size} < {min_size}")
        if p_value > alpha:
            reasons.append(f"p {p_value:.4g} > {alpha}")
        if lift_value < min_lift:
            reasons.append(f"lift {lift_value:.3f} < {min_lift}")
        if abs(mcc) < min_mcc:
            reasons.append(f"|mcc| {abs(mcc):.3f} < {min_mcc}")
        aligned = explainer._aligns(key, click_rows)
        if not aligned:
            reasons.append("corroborating signals do not align")
        results.append(
            {
                "intent": key,
                "tp": table.tp,
                "pattern_size": table.pattern_size,
                "candidate_size": table.candidate_size,
                "lift": round(lift_value, 6),
                "p": round(p_value, 6),
                "mcc": round(mcc, 6),
                "aligned": aligned,
                "gate_passed": not reasons,
                "rejected_because": reasons,
            }
        )
    return sorted(
        results,
        key=lambda item: (
            not item["gate_passed"],
            -item["lift"] * abs(item["mcc"]),
            item["intent"],
        ),
    )


class RealCatalogProof:
    def __init__(self, records, bundle):
        self.records = records
        self.bundle = bundle
        self.explainer = IntentExplainer(bundle)
        self.values = bundle["values"]
        self.masks = bundle["masks"]
        self.features = self.explainer.features
        self.eligible = eligible_rows(bundle)
        self.items = []

    def band(self, predicate):
        return [
            index
            for index in range(len(self.records))
            if self.eligible[index] and predicate(self.features[index])
        ]

    def run_one(
        self,
        key,
        title,
        given,
        expected,
        groups,
        kind="destination_visit",
        status="verified",
    ):
        states = [
            _state_from_rows(self.values, self.masks, rows, kind)
            for rows in groups
        ]
        clusters = _clusters(states)
        signals = _signals(self.records, groups, kind)
        selected_ids = [
            self.records[row]["id"] for rows in groups for row in rows
        ]
        explanations = self.explainer.explain_all(
            clusters, signals, selected_ids
        )
        click_rows = [row for rows in groups for row in rows]
        diagnostics = []
        for state in states:
            diagnostics.append(
                _diagnostics(self.explainer, state.x, click_rows)
            )
        item = {
            "key": key,
            "title": title,
            "given": given,
            "expected": expected,
            "status": status,
            "selected_plans": [
                _summary(self.records[row])
                for rows in groups
                for row in rows
            ],
            "observed": {
                "intents": [item["intent"] for item in explanations],
                "explanations": [
                    {
                        "cluster_id": item["cluster_id"],
                        "intent": item["intent"],
                        "message": item["message"],
                        "plan_count": len(item["plan_ids"]),
                        "confidence": item["confidence"],
                    }
                    for item in explanations
                ],
                "diagnostics": diagnostics,
            },
        }
        self.items.append(item)
        return item

    def run(self):
        premium = self.band(
            lambda f: f.price_pct is not None
            and f.spec_pct is not None
            and f.price_pct > 0.70
            and f.spec_pct > 0.70
        )
        value = self.band(
            lambda f: f.price_pct is not None
            and f.spec_pct is not None
            and f.spec_pct - f.price_pct > 0.15
        )
        low_price = self.band(
            lambda f: f.price_pct is not None and f.price_pct < 0.30
        )
        overpriced = self.band(
            lambda f: f.price_pct is not None
            and f.spec_pct is not None
            and f.price_pct > 0.70
            and f.spec_pct < 0.40
        )
        pure_cheap = self.band(
            lambda f: f.price_pct is not None
            and f.spec_pct is not None
            and f.price_pct < 0.30
            and f.spec_pct < 0.30
        )

        # Cold start needs the prior state, not an empty cluster list.
        prior_state = UserState(
            self.bundle["space"].prior(self.values, self.masks)
        )
        prior_state.activity = 1.0
        prior_clusters = _clusters([prior_state])
        prior_explanations = self.explainer.explain_all(prior_clusters, [], [])
        self.items.append(
            {
                "key": "real_cold_start",
                "title": "Cold start روی کاتالوگ واقعی",
                "given": "پروفایل خالی؛ state اولیه از prior",
                "expected": "exploring",
                "status": "verified",
                "selected_plans": [],
                "observed": {
                    "intents": [i["intent"] for i in prior_explanations],
                    "explanations": [
                        {
                            "cluster_id": i["cluster_id"],
                            "intent": i["intent"],
                            "message": i["message"],
                            "plan_count": len(i["plan_ids"]),
                            "confidence": i["confidence"],
                        }
                        for i in prior_explanations
                    ],
                    "diagnostics": [
                        _diagnostics(self.explainer, prior_state.x, [])
                    ],
                },
            }
        )

        self.run_one(
            "real_premium_clicks",
            "کلیک روی پلن‌های پرقدرت واقعی",
            "۵ پلن با price_pct>0.7 و spec_pct>0.7",
            "premium",
            [premium[:5]],
        )
        self.run_one(
            "real_premium_search",
            "جست‌وجو روی پلن‌های پرقدرت واقعی",
            "۵ نتیجه‌ی جست‌وجو از همان پلن‌ها",
            "premium",
            [premium[:5]],
            kind="search_impression",
        )
        self.run_one(
            "real_premium_details",
            "مشاهده‌ی جزئیات پلن‌های پرقدرت واقعی",
            "۵ مشاهده‌ی جزئیات",
            "premium",
            [premium[:5]],
            kind="details_view",
        )
        self.run_one(
            "real_value",
            "کلیک روی پلن‌های value واقعی",
            "۵ پلن با spec_pct - price_pct > 0.15",
            "value",
            [value[:5]],
        )
        self.run_one(
            "real_low_price",
            "کلیک روی ارزان‌ترین پلن‌های واقعی",
            "۵ پلن با price_pct<0.3",
            "value (این پلن‌ها مشخصات بالایی دارند)",
            [low_price[:5]],
        )
        self.run_one(
            "real_overpriced",
            "کلیک روی پلن‌های گران و ضعیف واقعی",
            "۵ پلن با price_pct>0.7 و spec_pct<0.4",
            "exploring و بدون value",
            [overpriced[:5]],
        )
        self.run_one(
            "real_two_interests",
            "دو علاقه‌ی هم‌زمان روی کاتالوگ واقعی",
            "۵ پلن ارزان + ۵ پلن پرقدرت",
            "value و premium",
            [low_price[:5], premium[:5]],
        )
        item = self.run_one(
            "real_pure_cheap_limit",
            "بخش «ارزان خالص» زیر حد آماری",
            "۵ پلن با price_pct<0.3 و spec_pct<0.3",
            "exploring (pattern_size کوچک‌تر از حد)",
            [pure_cheap[:5]],
            status="known_limit",
        )

        first = self.run_one(
            "real_deterministic_a",
            "تکرارپذیری (اجرای اول)",
            "همان ورودی پرقدرت",
            "premium",
            [premium[:5]],
            status="verified",
        )
        second = self.run_one(
            "real_deterministic_b",
            "تکرارپذیری (اجرای دوم)",
            "همان ورودی پرقدرت",
            "premium",
            [premium[:5]],
            status="verified",
        )
        self.items[-2]["duplicate_of"] = "real_deterministic_b"
        self.items[-1]["duplicate_of"] = "real_deterministic_a"
        first["observed"]["deterministic_pair_equal"] = (
            first["observed"]["intents"] == second["observed"]["intents"]
        )
        second["observed"]["deterministic_pair_equal"] = (
            first["observed"]["intents"] == second["observed"]["intents"]
        )

        bands = {
            "premium_rows": len(premium),
            "value_rows": len(value),
            "low_price_rows": len(low_price),
            "overpriced_rows": len(overpriced),
            "pure_cheap_rows": len(pure_cheap),
        }
        for item in self.items:
            item["passed"] = self._evaluate(item, bands)
        return self.items, bands

    @staticmethod
    def _evaluate(item, bands):
        intents = item["observed"]["intents"]
        key = item["key"]
        if key == "real_cold_start":
            return intents == ["exploring"]
        if key in {
            "real_premium_clicks",
            "real_premium_search",
            "real_premium_details",
            "real_deterministic_a",
            "real_deterministic_b",
        }:
            return intents[:1] == ["premium"]
        if key == "real_value":
            return intents[:1] == ["value"]
        if key == "real_low_price":
            return intents[:1] == ["value"]
        if key == "real_overpriced":
            return intents[:1] == ["exploring"] and "value" not in intents
        if key == "real_two_interests":
            return {"value", "premium"}.issubset(set(intents))
        if key == "real_pure_cheap_limit":
            return intents == ["exploring"]
        return False


def _environment(records, bands):
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        commit = "unknown"
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": platform.python_version(),
        "django": django.get_version(),
        "git_commit": commit,
        "mode": "read-only real catalog",
        "catalog": {
            "published_plans": len(records),
            "band_sizes": bands,
            "feature_coverage": _coverage(records),
        },
        "thresholds": {
            "explain_min_pattern_size": conf.explain_min_pattern_size(),
            "explain_alpha": conf.explain_alpha(),
            "explain_min_lift": conf.explain_min_lift(),
            "explain_min_mcc": conf.explain_min_mcc(),
            "explain_min_clicks": conf.explain_min_clicks(),
            "explain_k": conf.explain_k(),
            "min_resource_dimensions": conf.min_resource_dimensions(),
        },
    }


def _coverage(records):
    mapper = PlanFeatureMapper()
    features = [mapper.map(record) for record in records]
    return {
        field: sum(1 for feature in features if feature.get(field) is not None)
        for field in ("price", "cpu", "ram", "disk", "traffic")
    }


def _write_json(report):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "recommendation-proof-real-catalog.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def _badge(item):
    if not item["passed"]:
        return '<span class="badge fail">FAIL</span>'
    if item["status"] == "known_limit":
        return '<span class="badge limit">LIMIT (expected)</span>'
    return '<span class="badge ok">VERIFIED</span>'


def _fmt(value):
    if value is None:
        return "—"
    return str(value)


def _write_html(report):
    env = report["environment"]
    items = report["scenarios"]
    verified = [i for i in items if i["status"] == "verified"]
    verified_passed = sum(1 for i in verified if i["passed"])
    limits = [i for i in items if i["status"] == "known_limit"]
    limits_passed = sum(1 for i in limits if i["passed"])
    failed = [i for i in items if not i["passed"]]
    rows = []
    cards = []
    for index, item in enumerate(items, start=1):
        intents = ", ".join(item["observed"]["intents"]) or "—"
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(item['title'])}</td>"
            f"<td>{html.escape(str(item['expected']))}</td>"
            f"<td><code>{html.escape(intents)}</code></td>"
            f"<td>{_badge(item)}</td>"
            "</tr>"
        )
        plan_rows = "".join(
            "<tr>"
            f"<td>{plan['id']}</td>"
            f"<td>{html.escape(str(plan['name'] or '—'))}</td>"
            f"<td>{html.escape(str(plan['price'] or '—'))}</td>"
            f"<td>{html.escape(str(plan['cpu'] or '—'))}</td>"
            f"<td>{html.escape(str(plan['ram'] or '—'))}</td>"
            f"<td>{html.escape(str(plan['disk'] or '—'))}</td>"
            "</tr>"
            for plan in item["selected_plans"]
        )
        explanation_rows = "".join(
            "<tr>"
            f"<td>{explanation['cluster_id']}</td>"
            f"<td><code>{html.escape(explanation['intent'])}</code></td>"
            f"<td>{html.escape(explanation['message'])}</td>"
            f"<td>{explanation['plan_count']}</td>"
            f"<td>{html.escape(_fmt(explanation['confidence']))}</td>"
            "</tr>"
            for explanation in item["observed"]["explanations"]
        )
        diagnostic_blocks = []
        for state_index, diagnostics in enumerate(
            item["observed"].get("diagnostics") or []
        ):
            diagnostic_rows = "".join(
                "<tr>"
                f"<td><code>{html.escape(d['intent'])}</code></td>"
                f"<td>{d['tp']}/{d['pattern_size']}</td>"
                f"<td>{d['lift']}</td>"
                f"<td>{d['p']}</td>"
                f"<td>{d['mcc']}</td>"
                f"<td>{'✅' if d['gate_passed'] else '❌'}</td>"
                f"<td>{html.escape('؛ '.join(d['rejected_because']) or '—')}</td>"
                "</tr>"
                for d in diagnostics
            )
            diagnostic_blocks.append(
                f"<h4>کلاستر {state_index}</h4>"
                "<table class=\"inner\"><thead><tr>"
                "<th>intent</th><th>tp/pattern</th><th>lift</th><th>p</th>"
                "<th>mcc</th><th>gate</th><th>دلیل رد</th>"
                "</tr></thead><tbody>"
                f"{diagnostic_rows}</tbody></table>"
            )
        cards.append(
            "<details class=\"card\" "
            f"{'open' if not item['passed'] else ''}>"
            "<summary>"
            f"<span class=\"num\">{index}</span>"
            f"<span class=\"title\">{html.escape(item['title'])}</span>"
            f"{_badge(item)}"
            "</summary>"
            "<div class=\"body\">"
            f"<p><strong>ورودی:</strong> {html.escape(str(item['given']))}</p>"
            f"<p><strong>انتظار:</strong> {html.escape(str(item['expected']))}</p>"
            f"<p><strong>intentهای دیده‌شده:</strong> <code>{html.escape(intents)}</code></p>"
            + (
                "<h4>پلن‌های انتخاب‌شده از کاتالوگ واقعی</h4>"
                "<table class=\"inner\"><thead><tr><th>id</th><th>نام</th>"
                "<th>قیمت</th><th>CPU</th><th>RAM</th><th>Disk</th></tr></thead>"
                f"<tbody>{plan_rows}</tbody></table>"
                if plan_rows
                else ""
            )
            + (
                "<h4>توضیح‌های تولیدشده</h4>"
                "<table class=\"inner\"><thead><tr><th>cluster</th><th>intent</th>"
                "<th>پیام</th><th>پلن</th><th>confidence</th></tr></thead>"
                f"<tbody>{explanation_rows}</tbody></table>"
                if explanation_rows
                else ""
            )
            + "<h4>تشخیص دروازه‌های آماری</h4>"
            + "".join(diagnostic_blocks)
            + "<details class=\"raw\"><summary>شواهد خام JSON</summary>"
            f"<pre>{html.escape(json.dumps(item, ensure_ascii=False, indent=2))}</pre>"
            "</details></div></details>"
        )

    thresholds = "".join(
        f"<li><code>{html.escape(key)}</code> = {html.escape(str(value))}</li>"
        for key, value in env["thresholds"].items()
    )
    band_rows = "".join(
        f"<tr><td><code>{html.escape(key)}</code></td><td>{value}</td></tr>"
        for key, value in env["catalog"]["band_sizes"].items()
    )
    document = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>گواه عملکرد روی کاتالوگ واقعی</title>
<style>
  :root {{
    --bg: #0b1020; --panel: #121a30; --panel2: #0f1730; --text: #e8ecf7;
    --muted: #93a0bd; --line: #223052; --ok: #1f8a5b; --fail: #b03030;
    --limit: #a06a10; --accent: #7aa2ff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: radial-gradient(1200px 600px at 80% -10%, #1b2a52 0%, var(--bg) 60%);
    color: var(--text); font-family: Vazirmatn, Tahoma, system-ui, sans-serif;
    line-height: 1.8; padding: 32px 18px 80px;
  }}
  .wrap {{ max-width: 1150px; margin: 0 auto; }}
  h1 {{ font-size: 30px; margin: 0 0 6px; }}
  h2 {{ margin-top: 30px; }}
  h4 {{ margin: 16px 0 6px; color: var(--muted); }}
  .sub {{ color: var(--muted); margin: 0 0 24px; }}
  .hero {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 18px 0 24px; }}
  .stat {{ background: linear-gradient(180deg, var(--panel), var(--panel2)); border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px; }}
  .stat .k {{ color: var(--muted); font-size: 13px; }}
  .stat .v {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
  .stat .v.ok {{ color: #4ade80; }}
  .grid {{ display: grid; gap: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: right; padding: 10px 8px; border-bottom: 1px solid var(--line); font-size: 14px; vertical-align: top; }}
  th {{ color: var(--muted); font-weight: 600; }}
  code {{ background: #0a1226; border: 1px solid var(--line); padding: 1px 6px; border-radius: 6px; font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap; }}
  .badge.ok {{ background: rgba(31,138,91,.18); color: #4ade80; border: 1px solid rgba(74,222,128,.35); }}
  .badge.fail {{ background: rgba(176,48,48,.18); color: #f87171; border: 1px solid rgba(248,113,113,.35); }}
  .badge.limit {{ background: rgba(160,106,16,.2); color: #fbbf24; border: 1px solid rgba(251,191,36,.35); }}
  .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }}
  .card summary {{ cursor: pointer; list-style: none; display: flex; gap: 12px; align-items: center; padding: 14px 16px; }}
  .card summary::-webkit-details-marker {{ display: none; }}
  .card .num {{ width: 28px; height: 28px; border-radius: 8px; background: #0a1226; border: 1px solid var(--line); display: grid; place-items: center; font-size: 13px; color: var(--accent); }}
  .card .title {{ flex: 1; font-weight: 600; }}
  .card .body {{ padding: 0 16px 16px; border-top: 1px solid var(--line); }}
  .card .body p {{ margin: 10px 0; }}
  .inner {{ margin: 8px 0 14px; background: #0a1226; border: 1px solid var(--line); border-radius: 10px; }}
  .inner th, .inner td {{ padding: 7px; font-size: 13px; }}
  .raw summary {{ color: var(--accent); cursor: pointer; margin-top: 10px; }}
  pre {{ background: #070d1c; border: 1px solid var(--line); border-radius: 10px; padding: 12px; overflow: auto; direction: ltr; text-align: left; font-size: 12px; }}
  .muted {{ color: var(--muted); }}
  .note {{ background: rgba(122,162,255,.08); border: 1px solid rgba(122,162,255,.25); border-radius: 12px; padding: 14px 16px; margin: 20px 0; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 30px; }}
  @media print {{ body {{ background: #fff; color: #000; }} .card, .stat, table, pre {{ border-color: #ccc; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>گواه عملکرد روی کاتالوگ واقعی</h1>
  <p class="sub">اجرای فقط-خواندنی روی {env['catalog']['published_plans']} پلن منتشرشده‌ی واقعی؛ بدون هیچ نوشتن در دیتابیس.</p>

  <div class="hero">
    <div class="stat"><div class="k">سناریوهای تأییدشده</div><div class="v ok">{verified_passed} / {len(verified)}</div></div>
    <div class="stat"><div class="k">محدودیت مستندشده</div><div class="v" style="font-size:20px">{limits_passed} / {len(limits)}</div></div>
    <div class="stat"><div class="k">پلن‌های واقعی</div><div class="v">{env['catalog']['published_plans']}</div></div>
    <div class="stat"><div class="k">کامیت</div><div class="v" style="font-size:18px">{html.escape(env['git_commit'])}</div></div>
  </div>

  <div class="note">
    این گزارش هیچ رکوردی به دیتابیس اضافه نمی‌کند: نه پلن، نه پروفایل، نه سیگنال و نه فضای پیشنهاد.
    فضای پیشنهاد و stateها فقط در حافظه ساخته می‌شوند. پلن‌ها بر اساس percentile واقعی
    قیمت و مشخصات انتخاب شده‌اند، نه برچسب دستی.
  </div>

  <h2>اندازه‌ی بخش‌های واقعی</h2>
  <table><thead><tr><th>بخش</th><th>تعداد پلن</th></tr></thead><tbody>{band_rows}</tbody></table>

  <h2>خلاصه‌ی سناریوها</h2>
  <table>
    <thead><tr><th>#</th><th>سناریو</th><th>انتظار</th><th>intent دیده‌شده</th><th>نتیجه</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>جزئیات، پلن‌های واقعی و دروازه‌های آماری</h2>
  <div class="grid">{''.join(cards)}</div>

  <h2>آستانه‌های استفاده‌شده</h2>
  <ul>{thresholds}</ul>

  <footer>تولیدشده توسط <code>backend/scripts/generate_real_catalog_proof.py</code> — فقط-خواندنی و قابل تکرار.</footer>
</div>
</body>
</html>
"""
    path = OUTPUT_DIR / "recommendation-proof-real-catalog.html"
    path.write_text(document, encoding="utf-8")
    return path


def main():
    records = _records()
    if not records:
        raise SystemExit("no published plans found")
    bundle = _bundle(records)
    scenarios, bands = RealCatalogProof(records, bundle).run()
    report = {
        "title": "Recommendation System Proof (Real Catalog, Read-Only)",
        "environment": _environment(records, bands),
        "summary": {
            "verified_total": sum(
                1 for item in scenarios if item["status"] == "verified"
            ),
            "verified_passed": sum(
                1
                for item in scenarios
                if item["status"] == "verified" and item["passed"]
            ),
            "known_limits": sum(
                1 for item in scenarios if item["status"] == "known_limit"
            ),
            "known_limits_passed": sum(
                1
                for item in scenarios
                if item["status"] == "known_limit" and item["passed"]
            ),
            "failed": sum(1 for item in scenarios if not item["passed"]),
        },
        "scenarios": scenarios,
    }
    json_path = _write_json(report)
    html_path = _write_html(report)

    summary = report["summary"]
    print(
        "verified={verified_passed}/{verified_total} known_limits={known_limits_passed}/{known_limits} failed={failed}".format(
            **summary
        )
    )
    print(f"json: {json_path.relative_to(REPO_ROOT)}")
    print(f"html: {html_path.relative_to(REPO_ROOT)}")

    if summary["failed"]:
        for item in scenarios:
            if not item["passed"]:
                print(f"FAILED: {item['key']} -> {item['observed']['intents']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
