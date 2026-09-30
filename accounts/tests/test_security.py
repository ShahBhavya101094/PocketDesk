from django.test import RequestFactory, SimpleTestCase, override_settings

from accounts.security import client_ip


class ClientIPTests(SimpleTestCase):
    @override_settings(IS_VERCEL=False)
    def test_local_forwarding_headers_are_not_trusted(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="192.0.2.1", HTTP_X_VERCEL_FORWARDED_FOR="198.51.100.2"
        )
        self.assertEqual(client_ip(request), "192.0.2.1")

    @override_settings(IS_VERCEL=True)
    def test_vercel_header_is_used_only_on_vercel(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="192.0.2.1", HTTP_X_VERCEL_FORWARDED_FOR="198.51.100.2"
        )
        self.assertEqual(client_ip(request), "198.51.100.2")

    @override_settings(IS_VERCEL=True)
    def test_invalid_ip_is_rejected(self):
        request = RequestFactory().get("/", HTTP_X_VERCEL_FORWARDED_FOR="invalid,anything")
        self.assertIsNone(client_ip(request))
