from django.test import TestCase


class SiteConfigViewTests(TestCase):
    def test_public_site_config_exposes_frontend_runtime_values(self):
        response = self.client.get("/api/v1/catalog/site-config")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["catalog"]["pageSizes"])
        self.assertGreater(body["catalog"]["defaultPageSize"], 0)
        self.assertGreater(body["ops"]["siteRefreshMs"], 0)
        self.assertTrue(body["contact"]["email"])
