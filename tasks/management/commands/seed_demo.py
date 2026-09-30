"""Create local teaching fixtures without shipping a password in source control."""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from entries.models import Entry
from tasks.models import Task


class Command(BaseCommand):
    help = "Create local PocketDesk demo data. Requires DEBUG=True and an explicit password."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", help="Prefer DEMO_PASSWORD to avoid shell history.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Demo data is allowed only with DEBUG=True. Never run it in production."
            )
        username = options["username"].strip()
        password = options.get("password") or os.environ.get("DEMO_PASSWORD")
        if not username or not password:
            raise CommandError("Provide --username and --password, or set DEMO_PASSWORD.")
        user_model = get_user_model()
        candidate = user_model(username=username, first_name="Asha")
        try:
            candidate.full_clean(exclude=["password"], validate_unique=False)
            validate_password(password, candidate)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        username = candidate.username  # Use Django's normalized username for lookup, too.

        with transaction.atomic():
            user = user_model.objects.filter(username=username).first()
            if user is None:
                user = user_model.objects.create_user(
                    username=username, password=password, first_name="Asha"
                )
            elif not user.check_password(password):
                raise CommandError(
                    "That account exists; provide its password. Existing passwords are never changed."
                )
            if not user.is_active:
                raise CommandError("The existing account is inactive; no demo data was changed.")

            for title, completed in [
                ("Prepare Django demo", False),
                ("Read ORM notes", True),
                ("Submit workshop exercise", False),
            ]:
                if not Task.objects.filter(owner=user, title=title).exists():
                    Task.objects.create(owner=user, title=title, completed=completed)
            for key, value in {
                "course_link": "https://docs.djangoproject.com/en/5.2/",
                "project_name": "PocketDesk",
                "learning_goal": "Build my first REST API",
            }.items():
                Entry.objects.get_or_create(owner=user, key=key, defaults={"value": value})
        self.stdout.write(
            self.style.SUCCESS("Local demo ready. Existing records and passwords were preserved.")
        )
