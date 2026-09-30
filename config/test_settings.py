"""Deterministic isolated test configuration; never use this module to deploy."""

import os

# Do not read a developer's .env or connect to a production database in the test suite.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["DEBUG"] = "True"
os.environ["VERCEL"] = "0"
os.environ["DJANGO_SECRET_KEY"] = "test-only-key-not-a-production-secret"
os.environ.pop("DATABASE_URL", None)
os.environ["DJANGO_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["DJANGO_CSRF_TRUSTED_ORIGINS"] = ""

from .settings import *  # noqa: E402,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PUBLIC_SIGNUP_ENABLED = True
