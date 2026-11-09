from django.test import TestCase


class CatalogCorsTests(TestCase):
    def test_visitor_header_is_allowed_in_preflight(self):
        response = self.client.options(
            "/api/v1/catalog/plans",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-visitor-id",
        )

        self.assertEqual(response.status_code, 200)
        allowed = response.headers["Access-Control-Allow-Headers"].lower()
        self.assertIn("x-visitor-id", allowed)
