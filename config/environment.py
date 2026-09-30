"""Small, testable environment boundary; errors never echo secret values."""

import re
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


def boolean(environ, name, default=False):
    value = environ.get(name, str(default)).strip().lower()
    if value not in {"true", "false", "1", "0"}:
        raise ImproperlyConfigured(f"{name} must be true or false.")
    return value in {"true", "1"}


def comma_list(environ, name, default=""):
    return [item.strip() for item in environ.get(name, default).split(",") if item.strip()]


def runtime_settings(environ, base_dir):
    """Return deployment-sensitive settings without contacting the database."""
    vercel = environ.get("VERCEL") == "1"
    debug = boolean(environ, "DEBUG", False)
    if vercel and debug:
        raise ImproperlyConfigured("DEBUG must be false on Vercel.")
    production = vercel or not debug
    secret_key = environ.get("DJANGO_SECRET_KEY", "")
    if not secret_key or secret_key.startswith("replace-"):
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a newly generated secret.")
    if production and (
        len(secret_key) < 50
        or len(set(secret_key)) < 5
        or secret_key.startswith("django-insecure-")
    ):
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is too weak for production.")

    hosts = comma_list(
        environ, "DJANGO_ALLOWED_HOSTS", "" if production else "localhost,127.0.0.1,[::1]"
    )
    if not hosts or any(
        not re.fullmatch(r"(?:[a-zA-Z0-9][a-zA-Z0-9.-]*|\[[0-9a-fA-F:]+\])", host)
        or host.startswith(".")
        for host in hosts
    ):
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must contain explicit hostnames, no wildcards."
        )

    origins = comma_list(environ, "DJANGO_CSRF_TRUSTED_ORIGINS")
    if production and not origins:
        raise ImproperlyConfigured(
            "Set DJANGO_CSRF_TRUSTED_ORIGINS to the HTTPS deployment origins."
        )
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            valid_port = parsed.port is None or 1 <= parsed.port <= 65535
        except ValueError:
            raise ImproperlyConfigured("Invalid DJANGO_CSRF_TRUSTED_ORIGINS origin.") from None
        if (
            parsed.scheme not in ({"https"} if production else {"http", "https"})
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or "*" in origin
            or not valid_port
            or parsed.hostname not in {host.strip("[]").lower() for host in hosts}
        ):
            raise ImproperlyConfigured(
                "CSRF origins must be explicit origins matching allowed hosts."
            )

    database_url = environ.get("DATABASE_URL", "").strip()
    if not database_url:
        if production:
            raise ImproperlyConfigured("Set DATABASE_URL to a persistent PostgreSQL database.")
        database = {"ENGINE": "django.db.backends.sqlite3", "NAME": base_dir / "db.sqlite3"}
    else:
        try:
            parsed_database = urlsplit(database_url)
            if parsed_database.scheme not in {"postgres", "postgresql"}:
                raise ValueError
            if not parsed_database.hostname or not parsed_database.path.strip("/"):
                raise ValueError
            database = dj_database_url.parse(database_url, conn_max_age=0)
        except (ValueError, KeyError):
            raise ImproperlyConfigured(
                "DATABASE_URL must be a valid PostgreSQL connection URL."
            ) from None
        options = database.setdefault("OPTIONS", {})
        if production:
            if options.get("sslmode", "require") not in {"require", "verify-ca", "verify-full"}:
                raise ImproperlyConfigured(
                    "Production DATABASE_URL must require TLS (sslmode=require or stronger)."
                )
            options.setdefault("sslmode", "require")
        options.setdefault("connect_timeout", 10)
        # Request-scoped connections and no server-side cursors work with transaction poolers.
        database["DISABLE_SERVER_SIDE_CURSORS"] = True

    return {
        "DEBUG": debug,
        "IS_VERCEL": vercel,
        "IS_PRODUCTION": production,
        "SECRET_KEY": secret_key,
        "ALLOWED_HOSTS": hosts,
        "CSRF_TRUSTED_ORIGINS": origins,
        "DATABASES": {"default": database},
        "PUBLIC_SIGNUP_ENABLED": boolean(environ, "PUBLIC_SIGNUP_ENABLED", not production),
    }
