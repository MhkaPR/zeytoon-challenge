from django.test import TestCase

from apps.accounts.models import User
from apps.catalog.models import PublishedRecord
from apps.companies.models import Company
from apps.pipeline.models import Link, Site


class SiteConfigViewTests(TestCase):
    def test_public_site_config_exposes_frontend_runtime_values(self):
        response = self.client.get("/api/v1/catalog/site-config")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["catalog"]["pageSizes"])
        self.assertGreater(body["catalog"]["defaultPageSize"], 0)
        self.assertGreater(body["ops"]["siteRefreshMs"], 0)
        self.assertTrue(body["contact"]["email"])


class PublishedCatalogPaginationTests(TestCase):
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
            site=self.site,
            url="https://example.com/plans",
            url_hash="hash",
        )
        for index in range(15):
            PublishedRecord.objects.create(
                site=self.site.pk,
                link=self.link.pk,
                trace=0,
                classification=0,
                plan_type="hosting",
                natural_key=f"plan-{index}",
                values={"price_amount": 1000 + index},
                is_published=True,
            )

    def test_page_size_is_capped_at_twelve(self):
        response = self.client.get("/api/v1/catalog/plans?page_size=100")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 12)
        self.assertEqual(body["page"]["page_size"], 12)
        self.assertEqual(body["page"]["count"], 15)

    def test_companies_endpoint_is_paginated_and_serialized(self):
        response = self.client.get("/api/v1/catalog/companies")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["page"]["count"], 1)
        self.assertEqual(
            body["data"],
            [
                {
                    "domain": "example.com",
                    "company_name": "Example Co",
                    "plan_count": 15,
                }
            ],
        )
