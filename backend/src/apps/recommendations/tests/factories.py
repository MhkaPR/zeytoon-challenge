"""Shared fixtures for recommendation tests."""

from apps.accounts.models import User
from apps.catalog.models import PublishedRecord
from apps.companies.models import Company
from apps.pipeline.models import Link, Site


def catalog(*plans):
    """Create a company/site/link and one published record per plan tuple."""
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
    site = Site.objects.create(company=company, domain="example.com")
    link = Link.objects.create(
        site=site, url="https://example.com/plans", url_hash="hash"
    )
    records = []
    for index, values in enumerate(plans):
        records.append(
            PublishedRecord.objects.create(
                site=site.pk,
                link=link.pk,
                trace=0,
                classification=0,
                plan_type=values.get("plan_type", "hosting"),
                natural_key=f"plan-{index}",
                values=values,
                is_published=True,
            )
        )
    return records
