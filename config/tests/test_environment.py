import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.environment import boolean, runtime_settings


class EnvironmentTests(SimpleTestCase):
    def production(self, **extra):
        return {
            "DEBUG": "False",
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "DATABASE_URL": "postgresql://demo:example@db.example.com/pocketdesk?sslmode=require",
            "DJANGO_ALLOWED_HOSTS": "pocketdesk.example.com",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://pocketdesk.example.com",
            **extra,
        }

    def test_boolean_rejects_typo_instead_of_enabling_debug(self):
        with self.assertRaises(ImproperlyConfigured):
            boolean({"DEBUG": "tru"}, "DEBUG")

    def test_missing_secret_is_rejected_even_locally(self):
        with self.assertRaises(ImproperlyConfigured):
            runtime_settings({"DEBUG": "True"}, Path("/tmp"))

    def test_local_sqlite_and_signup_defaults(self):
        config = runtime_settings(
            {"DEBUG": "True", "DJANGO_SECRET_KEY": "local-test-key"}, Path("/tmp")
        )
        self.assertTrue(config["PUBLIC_SIGNUP_ENABLED"])
        self.assertEqual(config["DATABASES"]["default"]["ENGINE"], "django.db.backends.sqlite3")

    def test_vercel_never_allows_debug(self):
        with self.assertRaises(ImproperlyConfigured):
            runtime_settings(self.production(DEBUG="True"), Path("/tmp"))

    def test_production_has_secure_defaults(self):
        config = runtime_settings(self.production(), Path("/tmp"))
        self.assertFalse(config["PUBLIC_SIGNUP_ENABLED"])
        self.assertFalse(config["DEBUG"])
        database = config["DATABASES"]["default"]
        self.assertEqual(database["CONN_MAX_AGE"], 0)
        self.assertEqual(database["OPTIONS"]["sslmode"], "require")
        self.assertTrue(database["DISABLE_SERVER_SIDE_CURSORS"])

    def test_production_settings_enable_security_without_database_connection(self):
        path = Path(__file__).resolve().parents[1] / "settings.py"
        spec = importlib.util.spec_from_file_location("config.production_settings_test", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, self.production(), clear=True):
            spec.loader.exec_module(module)
        self.assertTrue(module.SECURE_SSL_REDIRECT)
        self.assertTrue(module.SESSION_COOKIE_SECURE)
        self.assertTrue(module.CSRF_COOKIE_SECURE)
        self.assertEqual(module.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertFalse(module.USE_X_FORWARDED_HOST)
        self.assertEqual(module.SECURE_HSTS_SECONDS, 3600)
        self.assertFalse(module.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertFalse(module.PUBLIC_SIGNUP_ENABLED)
        self.assertEqual(
            module.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"][0],
            "rest_framework.authentication.TokenAuthentication",
        )

    def test_tls_added_if_provider_did_not_add_it(self):
        config = runtime_settings(
            self.production(DATABASE_URL="postgres://demo:example@db.example.com/pocketdesk"),
            Path("/tmp"),
        )
        self.assertEqual(config["DATABASES"]["default"]["OPTIONS"]["sslmode"], "require")

    def test_production_rejects_unsafe_or_incomplete_configuration(self):
        cases = [
            {"DJANGO_SECRET_KEY": "short"},
            {"DJANGO_SECRET_KEY": "a" * 60},
            {"DJANGO_SECRET_KEY": "django-insecure-" + "abcdefghij" * 6},
            {"DATABASE_URL": ""},
            {"DATABASE_URL": "sqlite:///db.sqlite3"},
            {"DATABASE_URL": "postgresql://demo:example@db.example.com/pocketdesk?sslmode=disable"},
            {"DATABASE_URL": "postgresql://demo:example@/pocketdesk"},
            {"DJANGO_ALLOWED_HOSTS": ""},
            {"DJANGO_ALLOWED_HOSTS": "*"},
            {"DJANGO_ALLOWED_HOSTS": ".vercel.app"},
            {"DJANGO_ALLOWED_HOSTS": "https://pocketdesk.example.com"},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": ""},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "http://pocketdesk.example.com"},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://*.example.com"},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://other.example.com"},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://pocketdesk.example.com/path"},
        ]
        for values in cases:
            with self.subTest(names=list(values)), self.assertRaises(ImproperlyConfigured):
                runtime_settings(self.production(**values), Path("/tmp"))

    def test_error_does_not_reveal_database_credentials(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            runtime_settings(
                self.production(DATABASE_URL="notadb://private-user:private-pass@host/db"),
                Path("/tmp"),
            )
        self.assertNotIn("private", str(caught.exception))

    def test_disable_signup_locally(self):
        config = runtime_settings(
            {"DEBUG": "True", "DJANGO_SECRET_KEY": "local", "PUBLIC_SIGNUP_ENABLED": "False"},
            Path("/tmp"),
        )
        self.assertFalse(config["PUBLIC_SIGNUP_ENABLED"])
