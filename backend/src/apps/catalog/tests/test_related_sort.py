import uuid

import pytest
from django.test import TestCase

from apps.accounts.models import User
from apps.catalog.models import PublishedRecord
from apps.companies.models import Company
from apps.pipeline.models import Link, Site
from apps.recommendations.models import InterestProfile


class RelatedSortTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(
            username="owner", password="secret", phone_number="09120000001"
        )
        company = Company.objects.create(
            owner=owner,
            domain="example.com",
            company_name="Example Co",
            representative_name="Rep",
            phone_number="09120000000",
        )
        self.site = Site.objects.create(company=company, domain="example.com")
        self.link = Link.objects.create(
            site=self.site, url="https://example.com/plans", url_hash="hash"
        )
        self.plans = []
        for index in range(6):
            self.plans.append(
                PublishedRecord.objects.create(
                    site=self.site.pk,
                    link=self.link.pk,
                    trace=0,
                    classification=0,
                    plan_type="hosting",
                    natural_key=f"plan-{index}",
                    values={"price_amount": 10 + index, "ram_amount": index + 1},
                    is_published=True,
                )
            )

    def ids(self, response):
        return [plan["id"] for plan in response.json()["data"]]

    def test_cold_start_order_is_deterministic(self):
        first = self.client.get("/api/v1/catalog/plans")
        second = self.client.get("/api/v1/catalog/plans")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.ids(first), self.ids(second))

    def test_related_order_prefers_interested_plan(self):
        record = self.plans[0]
        visitor = uuid.uuid4()
        dim = self._dim()
        InterestProfile.objects.create(
            visitor_id=visitor,
            position=[0.0] * dim,
            uncertainty=[0.1] * dim,
            space_version=self._version(),
        )
        response = self.client.get(
            "/api/v1/catalog/plans", headers={"X-Visitor-Id": str(visitor)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response)[0], record.pk)

    def test_pages_do_not_repeat(self):
        first = self.client.get("/api/v1/catalog/plans?page=1&page_size=3")
        second = self.client.get("/api/v1/catalog/plans?page=2&page_size=3")
        overlap = set(self.ids(first)) & set(self.ids(second))
        self.assertEqual(overlap, set())

    def test_cookie_visitor_keeps_personalized_pagination(self):
        record = self.plans[0]
        visitor = uuid.uuid4()
        dim = self._dim()
        InterestProfile.objects.create(
            visitor_id=visitor,
            position=[0.0] * dim,
            uncertainty=[0.1] * dim,
            space_version=self._version(),
        )
        self.client.cookies["visitor_id"] = str(visitor)
        first = self.client.get("/api/v1/catalog/plans?page=1&page_size=3")
        second = self.client.get("/api/v1/catalog/plans?page=2&page_size=3")
        first_ids = self.ids(first)
        second_ids = self.ids(second)
        self.assertEqual(first_ids[0], record.pk)
        self.assertEqual(set(first_ids) & set(second_ids), set())

    def test_price_sorts_ignore_visitor(self):
        ascending = self.client.get("/api/v1/catalog/plans?sort=price")
        descending = self.client.get("/api/v1/catalog/plans?sort=expensive")
        prices = [
            plan["values"]["price_amount"] for plan in ascending.json()["data"]
        ]
        rev = [
            plan["values"]["price_amount"] for plan in descending.json()["data"]
        ]
        self.assertEqual(prices, sorted(prices))
        self.assertEqual(rev, sorted(rev, reverse=True))

    def _version(self):
        from apps.catalog.interfaces import CatalogInterface
        from apps.recommendations.services.v1.space import PlanSpace
        from apps.recommendations.services.v1.features import PlanFeatureMapper

        features = [
            PlanFeatureMapper().map(record)
            for record in CatalogInterface.published_plan_records()
        ]
        space = PlanSpace(n_bins=5).fit(features)
        self._dim_value = len(space.names)
        return space.version(features)

    def _dim(self):
        self._version()
        return self._dim_value
