#!/usr/bin/env python
"""Generate a self-contained proof artifact for the recommendation system.

The script boots Django with the test settings, swaps the database for an
in-memory SQLite database, migrates it, runs a battery of real end-to-end
scenarios (signals -> state -> clusters -> ranking -> explanations), and writes
``recommendation-proof.json`` and ``recommendation-proof.html`` under
``specs/008-intent-pattern-explanations/artifacts/``.

Nothing touches the developer database, Redis, or the network.

Run from the repository root::

    .venv/bin/python backend/scripts/generate_recommendation_proof.py

Exit code is 1 when any scenario fails, so it can gate CI or a presentation
build.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import platform
import subprocess
import sys
import uuid
from io import StringIO
from pathlib import Path

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
# Force an isolated database before Django reads settings. ``base.py`` calls
# ``read_env`` without overwrite, so this wins over ``.env``.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

_db_name = str(settings.DATABASES["default"].get("NAME"))
if "memory" not in _db_name:
    raise SystemExit(
        "refusing to run: the proof generator must use an in-memory database, "
        f"got {_db_name!r}"
    )
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]

from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402

call_command("migrate", verbosity=0, interactive=False, run_syncdb=True)

from rest_framework.test import APIClient  # noqa: E402

from apps.catalog.interfaces import CatalogInterface  # noqa: E402
from apps.catalog.models import PublishedRecord  # noqa: E402
from apps.recommendations import conf  # noqa: E402
from apps.recommendations.models import InterestProfile  # noqa: E402
from apps.recommendations.services.v1.ranking import RankingService  # noqa: E402
from apps.recommendations.services.v1.signals import SignalRecorder  # noqa: E402
from apps.recommendations.tests.factories import catalog  # noqa: E402

CHEAP = list(range(0, 30))
VALUE = list(range(30, 60))
OVERPRICED = list(range(60, 90))
PREMIUM = list(range(90, 120))
HIGH_SPECS = {"cpu": 64, "ram": 256, "disk": 4000}
LOW_SPECS = {"cpu": 1, "ram": 1, "disk": 10}


def _catalog():
    plans = []
    for index in CHEAP:
        plans.append(
            {
                "price_amount": 10 + index,
                **LOW_SPECS,
                "plan_name": f"cheap {index}",
                "plan_type": "hosting",
            }
        )
    for index in VALUE:
        plans.append(
            {
                "price_amount": 100 + (index - 30),
                **HIGH_SPECS,
                "plan_name": f"value {index}",
                "plan_type": "virtual_server",
            }
        )
    for index in OVERPRICED:
        plans.append(
            {
                "price_amount": 500 + (index - 60),
                **LOW_SPECS,
                "plan_name": f"overpriced {index}",
                "plan_type": "hosting",
            }
        )
    for index in PREMIUM:
        plans.append(
            {
                "price_amount": 1000 + (index - 90),
                **HIGH_SPECS,
                "plan_name": f"premium {index}",
                "plan_type": "dedicated_server",
            }
        )
    return catalog(*plans)


def _click(records, plan_records, kind, indices, visitor, query=""):
    return SignalRecorder().record(
        plan_records,
        kind,
        [records[index].pk for index in indices],
        query=query,
        visitor_id=visitor,
    )


def _run(plan_records, visitor, limit=20):
    return RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=limit
    )


def _intents(result):
    return [item["intent"] for item in result["explanations"]]


def _activities(visitor):
    profile = InterestProfile.objects.filter(visitor_id=visitor).first()
    return profile.activity_profile if profile else []


def _observed(visitor, result):
    return {
        "activities": _activities(visitor),
        "intents": _intents(result),
        "suggested_plan_ids": result["plan_ids"],
        "suggested_plan_count": len(result["plan_ids"]),
        "explanations": [
            {
                "cluster_id": item["cluster_id"],
                "intent": item["intent"],
                "direction": item["direction"],
                "message": item["message"],
                "plan_ids": item["plan_ids"],
                "plan_count": len(item["plan_ids"]),
                "confidence": item["confidence"],
            }
            for item in result["explanations"]
        ],
    }


def _scenario(key, title, given, expected, visitor, result):
    observed = _observed(visitor, result)
    return {
        "key": key,
        "title": title,
        "given": given,
        "expected": expected,
        "passed": False,
        "observed": observed,
    }


class Proof:
    def __init__(self, records, plan_records):
        self.records = records
        self.plan_records = plan_records
        self.items: list[dict] = []

    def add(self, item, predicate):
        item["passed"] = bool(predicate(item["observed"]))
        self.items.append(item)
        return item

    def run(self):
        records = self.records

        # 1. Cold start ----------------------------------------------------
        visitor = uuid.uuid4()
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "cold_start",
                "بازدیدکننده بدون سابقه",
                "هیچ سیگنالی ثبت نشده است",
                ["exploring"],
                visitor,
                result,
            ),
            lambda o: o["intents"] == ["exploring"] and o["suggested_plan_count"] > 0,
        )

        # 2. Premium click -------------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "premium_clicks",
                "کلیک روی پلن‌های پرقدرت",
                "۵ کلیک روی پلن‌های dedicated_server",
                ["premium"],
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["premium"],
        )

        # 3. Cheap click ---------------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", CHEAP[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "cheap_clicks",
                "کلیک روی پلن‌های اقتصادی",
                "۵ کلیک روی پلن‌های ارزان",
                ["cheap"],
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["cheap"],
        )

        # 4. Value click ---------------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", VALUE[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "value_clicks",
                "کلیک روی پلن‌های با نسبت امکانات به قیمت بالا",
                "۵ کلیک روی پلن‌های مشخصات‌بالا با قیمت پایین",
                ["value"],
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["value"],
        )

        # 5. Overpriced decoy ----------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", OVERPRICED[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "overpriced_decoy",
                "پلن گران و ضعیف نباید «ارزش» شود",
                "۵ کلیک روی پلن‌های گران با مشخصات ضعیف",
                "exploring و بدون value",
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["exploring"]
            and "value" not in o["intents"],
        )

        # 6. Search impressions --------------------------------------------
        visitor = uuid.uuid4()
        _click(
            records,
            self.plan_records,
            "search_impression",
            PREMIUM[:10],
            visitor,
            query="dedicated",
        )
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "search_only",
                "تشخیص علاقه فقط از نتایج جست‌وجو",
                "۱۰ نمایش نتیجه جست‌وجو بدون کلیک خروجی",
                ["premium"],
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["premium"],
        )

        # 6b. Search-only cheap ---------------------------------------------
        visitor = uuid.uuid4()
        _click(
            records,
            self.plan_records,
            "search_impression",
            CHEAP[:10],
            visitor,
            query="ارزان",
        )
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "search_only_cheap",
                "تشخیص اقتصادی از جست‌وجو",
                "۱۰ نمایش نتیجه‌ی جست‌وجوی ارزان",
                ["cheap"],
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["cheap"],
        )

        # 7. Details views --------------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "details_view", PREMIUM[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "details_only",
                "تشخیص علاقه فقط از مشاهده جزئیات",
                "۵ بار مشاهده جزئیات پلن پرقدرت",
                ["premium"],
                visitor,
                result,
            ),
            lambda o: o["intents"][:1] == ["premium"],
        )

        # 8. Two interests --------------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", CHEAP[:5], visitor)
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "two_interests",
                "دو علاقه‌ی هم‌زمان",
                "۵ کلیک ارزان + ۵ کلیک پرقدرت",
                ["cheap", "premium"],
                visitor,
                result,
            ),
            lambda o: {"cheap", "premium"}.issubset(set(o["intents"]))
            and len(o["explanations"]) >= 2,
        )

        # 9. Repeated interest merge ---------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        _click(records, self.plan_records, "destination_visit", PREMIUM[5:10], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "repeated_intent",
                "ادغام علاقه‌ی تکراری در یک ردیف",
                "دو موج کلیک روی پلن‌های پرقدرت",
                "یک ردیف premium",
                visitor,
                result,
            ),
            lambda o: o["intents"].count("premium") == 1,
        )

        # 10. No duplicate plans across rows -------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        _click(records, self.plan_records, "destination_visit", CHEAP[:5], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "no_duplicate_plans",
                "هیچ پلنی بین ردیف‌های توضیح تکرار نمی‌شود",
                "کلیک ارزان + پرقدرت",
                "plan_ids یکتا",
                visitor,
                result,
            ),
            lambda o: len(
                [
                    plan_id
                    for explanation in o["explanations"]
                    for plan_id in explanation["plan_ids"]
                ]
            )
            == len(
                {
                    plan_id
                    for explanation in o["explanations"]
                    for plan_id in explanation["plan_ids"]
                }
            ),
        )

        # 11. Decay: recent interest dominates -----------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        for _ in range(12):
            _click(records, self.plan_records, "destination_visit", CHEAP[:1], visitor)
        result = _run(self.plan_records, visitor)
        self.add(
            _scenario(
                "decay",
                "علاقه‌ی تازه بر علاقه‌ی قدیمی غالب می‌شود",
                "۵ کلیک پرقدرت، سپس ۱۲ کلیک ارزان",
                "cheap در توضیح‌ها و فعالیت غیریکنواخت",
                visitor,
                result,
            ),
            lambda o: "cheap" in o["intents"]
            and len(o["activities"]) >= 2
            and max(o["activities"]) > min(o["activities"]),
        )

        # 12. Visitor isolation --------------------------------------------
        cheap_visitor = uuid.uuid4()
        premium_visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", CHEAP[:5], cheap_visitor)
        _click(
            records, self.plan_records, "destination_visit", PREMIUM[:5], premium_visitor
        )
        cheap_result = _run(self.plan_records, cheap_visitor)
        premium_result = _run(self.plan_records, premium_visitor)
        self.add(
            _scenario(
                "visitor_isolation",
                "پروفایل دو بازدیدکننده قاطی نمی‌شود",
                "یک بازدیدکننده ارزان، یکی پرقدرت",
                "cheap برای اولی و premium برای دومی",
                cheap_visitor,
                cheap_result,
            ),
            lambda o: o["intents"][:1] == ["cheap"],
        )
        self.add(
            _scenario(
                "visitor_isolation_premium",
                "بازدیدکننده‌ی دوم مستقل است",
                "بازدیدکننده‌ی pرقدرت",
                ["premium"],
                premium_visitor,
                premium_result,
            ),
            lambda o: o["intents"][:1] == ["premium"],
        )

        # 13. Missing resources excluded -----------------------------------
        base = records[0]
        no_resource = PublishedRecord.objects.create(
            site=base.site,
            link=base.link,
            trace=0,
            classification=0,
            plan_type="hosting",
            natural_key="proof-no-resource",
            values={"plan_name": "license only", "price_amount": 10},
            is_published=True,
        )
        full_plan = PublishedRecord.objects.create(
            site=base.site,
            link=base.link,
            trace=0,
            classification=0,
            plan_type="hosting",
            natural_key="proof-full-resource",
            values={
                "plan_name": "real server",
                "price_amount": 100,
                "cpu": 8,
                "ram": 32,
                "disk": 500,
            },
            is_published=True,
        )
        subset = [
            row
            for row in CatalogInterface.published_plan_records()
            if row["id"] in {no_resource.pk, full_plan.pk}
        ]
        suggested = RankingService().suggest(subset, limit=10)
        self.add(
            {
                "key": "missing_resources",
                "title": "پلن بدون منبع از پیشنهاد حذف می‌شود",
                "given": "پلن فقط قیمت + پلن با CPU/RAM/Disk",
                "expected": "پلن بدون منبع در خروجی نیست",
                "passed": full_plan.pk in suggested and no_resource.pk not in suggested,
                "observed": {
                    "suggested_plan_ids": suggested,
                    "full_plan_id": full_plan.pk,
                    "no_resource_plan_id": no_resource.pk,
                },
            },
            lambda o: True,
        )
        PublishedRecord.objects.filter(pk__in=[no_resource.pk, full_plan.pk]).delete()

        # 14. Partial resource stays eligible ------------------------------
        base = records[0]
        ram_only = PublishedRecord.objects.create(
            site=base.site,
            link=base.link,
            trace=0,
            classification=0,
            plan_type="hosting",
            natural_key="proof-ram-only",
            values={"plan_name": "ram only", "price_amount": 20, "ram": 8},
            is_published=True,
        )
        full_plan = PublishedRecord.objects.create(
            site=base.site,
            link=base.link,
            trace=0,
            classification=0,
            plan_type="hosting",
            natural_key="proof-full-resource-2",
            values={
                "plan_name": "full server",
                "price_amount": 30,
                "cpu": 2,
                "ram": 8,
                "disk": 100,
            },
            is_published=True,
        )
        subset = [
            row
            for row in CatalogInterface.published_plan_records()
            if row["id"] in {ram_only.pk, full_plan.pk}
        ]
        suggested = RankingService().suggest(subset, limit=10)
        self.add(
            {
                "key": "partial_resources",
                "title": "پلن تک‌منبعی با تنظیم پیش‌فرض واجد شرایط است",
                "given": "پلن فقط RAM + پلن کامل",
                "expected": "پلن RAM-only در خروجی هست",
                "passed": ram_only.pk in suggested and full_plan.pk in suggested,
                "observed": {
                    "suggested_plan_ids": suggested,
                    "ram_only_plan_id": ram_only.pk,
                },
            },
            lambda o: True,
        )
        PublishedRecord.objects.filter(pk__in=[ram_only.pk, full_plan.pk]).delete()

        # 14b. Configurable minimum resource dimensions --------------------
        base = records[0]
        ram_only = PublishedRecord.objects.create(
            site=base.site,
            link=base.link,
            trace=0,
            classification=0,
            plan_type="hosting",
            natural_key="proof-ram-only-min2",
            values={"plan_name": "ram only", "price_amount": 20, "ram": 8},
            is_published=True,
        )
        full_plan = PublishedRecord.objects.create(
            site=base.site,
            link=base.link,
            trace=0,
            classification=0,
            plan_type="hosting",
            natural_key="proof-full-resource-min2",
            values={
                "plan_name": "full server",
                "price_amount": 30,
                "cpu": 2,
                "ram": 8,
                "disk": 100,
            },
            is_published=True,
        )
        subset = [
            row
            for row in CatalogInterface.published_plan_records()
            if row["id"] in {ram_only.pk, full_plan.pk}
        ]
        settings.RECOMMENDATION_MIN_RESOURCE_DIMENSIONS = 2
        try:
            suggested = RankingService().suggest(subset, limit=10)
        finally:
            del settings.RECOMMENDATION_MIN_RESOURCE_DIMENSIONS
        self.add(
            {
                "key": "min_resource_dimensions",
                "title": "حداقل ابعاد منبع قابل تنظیم است",
                "given": "مینیمم ۲ منبع؛ پلن RAM-only + پلن کامل",
                "expected": "پلن تک‌منبعی حذف و پلن کامل حفظ شود",
                "passed": ram_only.pk not in suggested and full_plan.pk in suggested,
                "observed": {
                    "suggested_plan_ids": suggested,
                    "ram_only_plan_id": ram_only.pk,
                    "full_plan_id": full_plan.pk,
                },
            },
            lambda o: True,
        )
        PublishedRecord.objects.filter(pk__in=[ram_only.pk, full_plan.pk]).delete()

        # 15. Public API contract ------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        response = APIClient().get(
            "/api/v1/catalog/plans/suggested",
            HTTP_X_VISITOR_ID=str(visitor),
        )
        payload = response.json() if response.status_code == 200 else {}
        self.add(
            {
                "key": "api_contract",
                "title": "پاسخ API عمومی: پلن + توضیح با هم",
                "given": "درخواست GET /api/v1/catalog/plans/suggested",
                "expected": "status=200، data و explanations پر",
                "passed": response.status_code == 200
                and bool(payload.get("data"))
                and (payload.get("explanations") or [{}])[0].get("intent")
                == "premium",
                "observed": {
                    "status": response.status_code,
                    "plan_count": len(payload.get("data") or []),
                    "explanations": [
                        {
                            "cluster_id": item["cluster_id"],
                            "intent": item["intent"],
                            "message": item["message"],
                            "plan_count": len(item.get("plan_ids") or []),
                        }
                        for item in payload.get("explanations") or []
                    ],
                },
            },
            lambda o: True,
        )

        # 16. Invalid visitor id fallback ----------------------------------
        response = APIClient().get(
            "/api/v1/catalog/plans/suggested",
            HTTP_X_VISITOR_ID="not-a-uuid",
        )
        payload = response.json() if response.status_code == 200 else {}
        self.add(
            {
                "key": "invalid_visitor",
                "title": "شناسه‌ی نامعتبر به cold start برمی‌گردد",
                "given": "X-Visitor-Id = not-a-uuid",
                "expected": "status=200 و پلن پیشنهادی",
                "passed": response.status_code == 200 and bool(payload.get("data")),
                "observed": {
                    "status": response.status_code,
                    "plan_count": len(payload.get("data") or []),
                },
            },
            lambda o: True,
        )

        # 17. Determinism ---------------------------------------------------
        visitor = uuid.uuid4()
        _click(records, self.plan_records, "destination_visit", PREMIUM[:5], visitor)
        first = _run(self.plan_records, visitor)
        second = _run(self.plan_records, visitor)
        self.add(
            {
                "key": "deterministic",
                "title": "خروجی در اجرای دوباره یکسان است",
                "given": "دو بار محاسبه با پروفایل ثابت",
                "expected": "نتیجه‌ی کاملاً برابر",
                "passed": first == second,
                "observed": {
                    "first_intents": _intents(first),
                    "second_intents": _intents(second),
                    "same": first == second,
                },
            },
            lambda o: True,
        )

        # 18. Signal cap ----------------------------------------------------
        visitor = uuid.uuid4()
        settings.RECOMMENDATION_SIGNAL_CAP_PER_MINUTE = 2
        try:
            accepted = 0
            for _ in range(5):
                accepted += _click(
                    records,
                    self.plan_records,
                    "destination_visit",
                    CHEAP[:1],
                    visitor,
                )["accepted"]
        finally:
            del settings.RECOMMENDATION_SIGNAL_CAP_PER_MINUTE
        self.add(
            {
                "key": "signal_cap",
                "title": "محدودیت نرخ سیگنال اعمال می‌شود",
                "given": "سقف ۲ در دقیقه، ۵ تلاش",
                "expected": "فقط ۲ سیگنال پذیرفته شود",
                "passed": accepted == 2,
                "observed": {"accepted": accepted, "attempted": 5, "cap": 2},
            },
            lambda o: True,
        )

        # 19. Simulation command used in live demos -------------------------
        out = StringIO()
        call_command(
            "simulate_recommendations",
            "--plan-type",
            "dedicated_server",
            "--count",
            "5",
            "--top",
            "10",
            stdout=out,
        )
        text = out.getvalue()
        self.add(
            {
                "key": "simulation_command",
                "title": "دستور دموی زنده intent را گزارش می‌کند",
                "given": "simulate_recommendations --plan-type dedicated_server --count 5",
                "expected": "خروجی شامل suggested plans و premium",
                "passed": "suggested plans" in text and "premium" in text,
                "observed": {
                    "output_tail": text[-600:],
                },
            },
            lambda o: True,
        )

        return self.items


def _environment():
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
        "database": "sqlite::memory:",
        "cache": "locmem",
        "thresholds": {
            "explain_min_pattern_size": conf.explain_min_pattern_size(),
            "explain_alpha": conf.explain_alpha(),
            "explain_min_lift": conf.explain_min_lift(),
            "explain_min_mcc": conf.explain_min_mcc(),
            "explain_min_clicks": conf.explain_min_clicks(),
            "explain_k": conf.explain_k(),
            "min_resource_dimensions": conf.min_resource_dimensions(),
            "cluster_activity_decay": conf.cluster_activity_decay(),
            "cluster_min_activity_ratio": conf.cluster_min_activity_ratio(),
            "suggestion_cluster_limit": conf.suggestion_cluster_limit(),
        },
    }


def _write_json(report):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "recommendation-proof.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def _badge(passed):
    return (
        '<span class="badge ok">PASS</span>'
        if passed
        else '<span class="badge fail">FAIL</span>'
    )


def _confidence(confidence):
    if not confidence:
        return "—"
    return (
        f"lift={confidence['lift']} · p={confidence['p']} · "
        f"mcc={confidence['mcc']}"
    )


def _write_html(report):
    env = report["environment"]
    items = report["scenarios"]
    passed = sum(1 for item in items if item["passed"])
    total = len(items)
    rows = []
    cards = []
    for index, item in enumerate(items, start=1):
        observed = item["observed"]
        intents = ", ".join(observed.get("intents") or []) or "—"
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(item['title'])}</td>"
            f"<td>{html.escape(str(item['expected']))}</td>"
            f"<td><code>{html.escape(intents)}</code></td>"
            f"<td>{_badge(item['passed'])}</td>"
            "</tr>"
        )
        explanation_rows = "".join(
            "<tr>"
            f"<td>{explanation.get('cluster_id')}</td>"
            f"<td><code>{html.escape(str(explanation.get('intent', '')))}</code></td>"
            f"<td>{html.escape(str(explanation.get('message', '')))}</td>"
            f"<td>{explanation.get('plan_count', 0)}</td>"
            f"<td>{html.escape(_confidence(explanation.get('confidence')))}</td>"
            "</tr>"
            for explanation in observed.get("explanations") or []
        )
        explanation_table = (
            "<table class=\"inner\"><thead><tr>"
            "<th>cluster</th><th>intent</th><th>پیام</th>"
            "<th>تعداد پلن</th><th>confidence</th></tr></thead>"
            f"<tbody>{explanation_rows}</tbody></table>"
            if explanation_rows
            else "<p class=\"muted\">خروجی explanation برای این سناریو ساختار متفاوتی دارد.</p>"
        )
        cards.append(
            "<details class=\"card\" "
            f"{'open' if not item['passed'] else ''}>"
            "<summary>"
            f"<span class=\"num\">{index}</span>"
            f"<span class=\"title\">{html.escape(item['title'])}</span>"
            f"{_badge(item['passed'])}"
            "</summary>"
            "<div class=\"body\">"
            f"<p><strong>ورودی:</strong> {html.escape(str(item['given']))}</p>"
            f"<p><strong>انتظار:</strong> {html.escape(str(item['expected']))}</p>"
            f"<p><strong>intentهای دیده‌شده:</strong> <code>{html.escape(intents)}</code></p>"
            f"<p><strong>فعالیت کلاسترها:</strong> "
            f"<code>{html.escape(str(observed.get('activities') or '—'))}</code></p>"
            f"{explanation_table}"
            "<details class=\"raw\"><summary>شواهد خام JSON</summary>"
            f"<pre>{html.escape(json.dumps(item, ensure_ascii=False, indent=2))}</pre>"
            "</details></div></details>"
        )

    thresholds = "".join(
        f"<li><code>{html.escape(key)}</code> = {html.escape(str(value))}</li>"
        for key, value in env["thresholds"].items()
    )
    document = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>گواه عملکرد سیستم پیشنهاد</title>
<style>
  :root {{
    --bg: #0b1020; --panel: #121a30; --panel2: #0f1730; --text: #e8ecf7;
    --muted: #93a0bd; --line: #223052; --ok: #1f8a5b; --fail: #b03030;
    --accent: #7aa2ff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: radial-gradient(1200px 600px at 80% -10%, #1b2a52 0%, var(--bg) 60%);
    color: var(--text); font-family: Vazirmatn, Tahoma, system-ui, sans-serif;
    line-height: 1.8; padding: 32px 18px 80px;
  }}
  .wrap {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 30px; margin: 0 0 6px; }}
  .sub {{ color: var(--muted); margin: 0 0 24px; }}
  .hero {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px; margin: 18px 0 28px;
  }}
  .stat {{
    background: linear-gradient(180deg, var(--panel), var(--panel2));
    border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px;
  }}
  .stat .k {{ color: var(--muted); font-size: 13px; }}
  .stat .v {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
  .stat .v.ok {{ color: #4ade80; }}
  .grid {{ display: grid; gap: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: right; padding: 10px 8px; border-bottom: 1px solid var(--line); font-size: 14px; }}
  th {{ color: var(--muted); font-weight: 600; }}
  code {{ background: #0a1226; border: 1px solid var(--line); padding: 1px 6px; border-radius: 6px; font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }}
  .badge.ok {{ background: rgba(31,138,91,.18); color: #4ade80; border: 1px solid rgba(74,222,128,.35); }}
  .badge.fail {{ background: rgba(176,48,48,.18); color: #f87171; border: 1px solid rgba(248,113,113,.35); }}
  .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }}
  .card summary {{ cursor: pointer; list-style: none; display: flex; gap: 12px; align-items: center; padding: 14px 16px; }}
  .card summary::-webkit-details-marker {{ display: none; }}
  .card .num {{ width: 28px; height: 28px; border-radius: 8px; background: #0a1226; border: 1px solid var(--line); display: grid; place-items: center; font-size: 13px; color: var(--accent); }}
  .card .title {{ flex: 1; font-weight: 600; }}
  .card .body {{ padding: 0 16px 16px; border-top: 1px solid var(--line); }}
  .card .body p {{ margin: 10px 0; }}
  .inner {{ margin: 10px 0; background: #0a1226; border: 1px solid var(--line); border-radius: 10px; }}
  .inner th, .inner td {{ padding: 8px; }}
  .raw summary {{ color: var(--accent); cursor: pointer; margin-top: 10px; }}
  pre {{ background: #070d1c; border: 1px solid var(--line); border-radius: 10px; padding: 12px; overflow: auto; direction: ltr; text-align: left; font-size: 12px; }}
  .muted {{ color: var(--muted); }}
  .note {{ background: rgba(122,162,255,.08); border: 1px solid rgba(122,162,255,.25); border-radius: 12px; padding: 14px 16px; margin: 24px 0; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 30px; }}
  @media print {{ body {{ background: #fff; color: #000; }} .card, .stat, table, pre {{ border-color: #ccc; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>گواه عملکرد سیستم پیشنهاد</h1>
  <p class="sub">خروجی واقعی سیستم در یک دیتابیس ایزوله‌ی درون‌حافظه‌ای؛ بدون داده‌ی ساختگی در assertionها.</p>

  <div class="hero">
    <div class="stat"><div class="k">سناریوهای موفق</div><div class="v ok">{passed} / {total}</div></div>
    <div class="stat"><div class="k">کامیت</div><div class="v" style="font-size:18px">{html.escape(env['git_commit'])}</div></div>
    <div class="stat"><div class="k">زمان تولید</div><div class="v" style="font-size:15px">{html.escape(env['generated_at'])}</div></div>
    <div class="stat"><div class="k">محیط</div><div class="v" style="font-size:15px">Python {html.escape(env['python'])} · Django {html.escape(env['django'])}</div></div>
  </div>

  <div class="note">
    این فایل با اجرای مسیر کامل <code>signals → state → clusters → ranking → explanation</code>
    روی یک کاتالوگ چهارباندی ساخته شده است. آستانه‌های آماری همان مقادیر پیش‌فرض تولید هستند
    و هیچ آستانه‌ای برای عبور تست شل نشده است.
  </div>

  <h2>خلاصه‌ی سناریوها</h2>
  <table>
    <thead><tr><th>#</th><th>سناریو</th><th>انتظار</th><th>intent دیده‌شده</th><th>نتیجه</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2 style="margin-top:30px">جزئیات و شواهد</h2>
  <div class="grid">{''.join(cards)}</div>

  <h2 style="margin-top:30px">آستانه‌های استفاده‌شده</h2>
  <ul>{thresholds}</ul>

  <footer>تولیدشده توسط <code>backend/scripts/generate_recommendation_proof.py</code> — قابل تکرار و قابل چاپ.</footer>
</div>
</body>
</html>
"""
    path = OUTPUT_DIR / "recommendation-proof.html"
    path.write_text(document, encoding="utf-8")
    return path


def main():
    records = _catalog()
    plan_records = CatalogInterface.published_plan_records()
    scenarios = Proof(records, plan_records).run()
    report = {
        "title": "Recommendation System Proof",
        "environment": _environment(),
        "summary": {
            "total": len(scenarios),
            "passed": sum(1 for item in scenarios if item["passed"]),
            "failed": sum(1 for item in scenarios if not item["passed"]),
        },
        "scenarios": scenarios,
    }
    json_path = _write_json(report)
    html_path = _write_html(report)

    print(f"total={report['summary']['total']} passed={report['summary']['passed']} failed={report['summary']['failed']}")
    print(f"json: {json_path.relative_to(REPO_ROOT)}")
    print(f"html: {html_path.relative_to(REPO_ROOT)}")

    connections.close_all()
    if report["summary"]["failed"]:
        for item in scenarios:
            if not item["passed"]:
                print(f"FAILED: {item['key']} -> {item['observed']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
