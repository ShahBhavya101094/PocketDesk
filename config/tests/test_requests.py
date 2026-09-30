import json
import logging

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase

from config.middleware import RequestLogMiddleware, SafeJSONFormatter


class LoggingTests(SimpleTestCase):
    def test_request_log_omits_all_sensitive_request_fields(self):
        request = RequestFactory().post(
            "/private-personal-path/?secret=do-not-log",
            {"password": "also-do-not-log"},
            HTTP_AUTHORIZATION="Token never-log-this",
            HTTP_X_REQUEST_ID="attacker-id",
        )
        middleware = RequestLogMiddleware(lambda req: HttpResponse("ok"))
        with self.assertLogs("pocketdesk.requests", level="INFO") as captured:
            response = middleware(request)
        record = json.loads(SafeJSONFormatter().format(captured.records[0]))
        self.assertEqual(record["status"], 200)
        self.assertEqual(record["method"], "POST")
        self.assertEqual(len(record["request_id"]), 32)
        self.assertEqual(record["request_id"], response["X-Request-ID"])
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertEqual(
            set(record),
            {
                "timestamp",
                "level",
                "logger",
                "event",
                "request_id",
                "method",
                "status",
                "duration_ms",
            },
        )
        self.assertNotIn("private", json.dumps(record))
        self.assertNotIn("attacker", json.dumps(record))

    def test_third_party_log_messages_cannot_leak_values(self):
        record = logging.LogRecord(
            "django.request", logging.WARNING, "", 1, "secret password", (), None
        )
        self.assertNotIn("secret", SafeJSONFormatter().format(record))


class RoutingTests(TestCase):
    def test_health_liveness_has_no_database_queries(self):
        with self.assertNumQueries(0):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertIn("X-Request-ID", response)

    def test_health_rejects_post(self):
        self.assertEqual(self.client.post("/healthz/").status_code, 405)

    def test_root_redirects_to_tasks(self):
        self.assertRedirects(self.client.get("/"), "/tasks/", fetch_redirect_response=False)

    def test_api_requires_authentication_and_advertises_token(self):
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Token")

    def test_unknown_host_is_rejected(self):
        self.assertEqual(
            self.client.get("/healthz/", HTTP_HOST="malicious.example").status_code, 400
        )
