from django.test import TestCase


class SignatureRouteTests(TestCase):
    def test_routes_are_exposed(self):
        self.assertEqual(self.client.get("/api/signatures/").status_code, 200)
        self.assertEqual(self.client.get("/signatures/").status_code, 200)
