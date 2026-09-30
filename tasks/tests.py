import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .forms import TaskForm
from .models import Task


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.asha = get_user_model().objects.create_user("asha", password="test-pass")
        cls.other = get_user_model().objects.create_user("other", password="test-pass")
        cls.task = Task.objects.create(owner=cls.asha, title="Prepare Django demo")
        cls.private = Task.objects.create(owner=cls.other, title="Other private task")

    def setUp(self):
        self.client.force_login(self.asha, backend="django.contrib.auth.backends.ModelBackend")
        self.api = APIClient()
        self.api.force_authenticate(self.asha)

    def test_form_normalizes_title_and_does_not_offer_owner(self):
        form = TaskForm({"title": "  Clear next action  ", "owner": self.other.pk})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["title"], "Clear next action")
        self.assertNotIn("owner", form.fields)

    def test_title_rejects_short_blank_and_long_input(self):
        for title in ["Go", "   ", "x" * 201]:
            with self.subTest(title=title[:10]):
                self.assertFalse(TaskForm({"title": title}).is_valid())
                self.assertEqual(self.api.post("/api/tasks/", {"title": title}).status_code, 400)

    def test_title_error_is_reported_once_on_the_field(self):
        form = TaskForm({"title": "Go"})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors["title"]), 1)
        self.assertNotIn("__all__", form.errors)

    def test_model_validation_normalizes_title(self):
        task = Task(owner=self.asha, title="  Read documentation  ")
        task.full_clean()
        self.assertEqual(task.title, "Read documentation")
        task.title = "No"
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_html_pages_require_login(self):
        self.client.logout()
        for name, kwargs in [
            ("list", {}),
            ("create", {}),
            ("update", {"pk": self.task.pk}),
            ("delete", {"pk": self.task.pk}),
        ]:
            self.assertEqual(
                self.client.get(reverse(f"tasks:{name}", kwargs=kwargs)).status_code, 302
            )

    def test_html_list_is_owner_scoped_and_has_counts(self):
        Task.objects.create(owner=self.asha, title="Read ORM notes", completed=True)
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["open_count"], 1)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertContains(response, self.task.title)
        self.assertNotContains(response, self.private.title)

    def test_html_search_status_and_invalid_page_are_safe(self):
        Task.objects.create(owner=self.asha, title="Read ORM notes", completed=True)
        response = self.client.get(
            reverse("tasks:list"), {"q": " ORM ", "status": "done", "page": "bad"}
        )
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertEqual(response.context["query"], "ORM")
        self.assertEqual(response.context["status"], "done")
        response = self.client.get(reverse("tasks:list"), {"status": "unknown"})
        self.assertEqual(response.context["status"], "all")

    def test_html_paginates_ten(self):
        Task.objects.bulk_create(
            [Task(owner=self.asha, title=f"Task number {n}") for n in range(12)]
        )
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertTrue(response.context["page_obj"].has_next())

    def test_html_create_and_update_cannot_forge_owner(self):
        response = self.client.post(
            reverse("tasks:create"), {"title": "  New task  ", "owner": self.other.pk}
        )
        self.assertRedirects(response, reverse("tasks:list"))
        task = Task.objects.get(title="New task")
        self.assertEqual(task.owner, self.asha)
        self.client.post(
            reverse("tasks:update", args=[task.pk]),
            {"title": "Updated task", "completed": "on", "owner": self.other.pk},
        )
        task.refresh_from_db()
        self.assertEqual(task.owner, self.asha)
        self.assertTrue(task.completed)

    def test_other_users_html_objects_return_404(self):
        for route in ["update", "delete", "toggle"]:
            self.assertEqual(
                self.client.post(
                    reverse(f"tasks:{route}", args=[self.private.pk]), {"title": "Changed"}
                ).status_code,
                404,
            )
        self.private.refresh_from_db()
        self.assertEqual(self.private.title, "Other private task")

    def test_delete_get_confirms_and_post_deletes(self):
        url = reverse("tasks:delete", args=[self.task.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_toggle_requires_post_and_updates_timestamp(self):
        url = reverse("tasks:toggle", args=[self.task.pk])
        before = self.task.updated_at
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.task.refresh_from_db()
        self.assertTrue(self.task.completed)
        self.assertGreater(self.task.updated_at, before)
        self.client.post(url)
        self.task.refresh_from_db()
        self.assertFalse(self.task.completed)

    def test_html_mutation_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.asha, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(client.post(reverse("tasks:toggle", args=[self.task.pk])).status_code, 403)
        self.assertEqual(
            client.post(reverse("tasks:create"), {"title": "Forged task"}).status_code, 403
        )

    def test_template_escapes_untrusted_titles(self):
        Task.objects.create(owner=self.asha, title='<script>alert("x")</script>')
        response = self.client.get(reverse("tasks:list"))
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_api_requires_authentication(self):
        self.assertEqual(APIClient().get("/api/tasks/").status_code, 401)

    def test_api_list_is_paginated_and_scoped(self):
        response = self.api.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.task.pk)
        self.assertNotIn("owner", response.data["results"][0])

    def test_api_pagination_counts_only_owned_records(self):
        Task.objects.bulk_create(
            [Task(owner=self.asha, title=f"Owned task {n}") for n in range(10)]
        )
        Task.objects.bulk_create(
            [Task(owner=self.other, title=f"Foreign task {n}") for n in range(12)]
        )
        response = self.api.get("/api/tasks/")
        self.assertEqual(response.data["count"], 11)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        second = self.api.get(response.data["next"])
        self.assertEqual(len(second.data["results"]), 1)
        self.assertIsNone(second.data["next"])
        ids = [row["id"] for row in response.data["results"] + second.data["results"]]
        self.assertEqual(Task.objects.filter(id__in=ids, owner=self.asha).count(), 11)

    def test_api_create_patch_and_delete(self):
        response = self.api.post(
            "/api/tasks/", {"title": "  API task  ", "owner": self.other.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.title, "API task")
        self.assertEqual(task.owner, self.asha)
        response = self.api.patch(
            f"/api/tasks/{task.pk}/", {"completed": True, "owner": self.other.pk}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertTrue(task.completed)
        self.assertEqual(task.owner, self.asha)
        self.assertEqual(self.api.delete(f"/api/tasks/{task.pk}/").status_code, 204)

    def test_api_other_user_detail_mutations_return_404(self):
        url = f"/api/tasks/{self.private.pk}/"
        self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.patch(url, {"completed": True}).status_code, 404)
        self.assertEqual(self.api.delete(url).status_code, 404)

    def test_api_search_and_ordering(self):
        Task.objects.create(owner=self.asha, title="Zebra study")
        response = self.api.get("/api/tasks/", {"search": "Zebra", "ordering": "-id"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Zebra study")

    def test_search_input_is_data_not_sql(self):
        query = "' OR 1=1 --"
        response = self.api.get("/api/tasks/", {"search": query})
        self.assertEqual(response.data["count"], 0)
        response = self.client.get(reverse("tasks:list"), {"q": query})
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertEqual(Task.objects.count(), 2)

    def test_token_authentication_and_invalid_token(self):
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=self.asha)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(client.get("/api/tasks/").status_code, 200)
        client.credentials(HTTP_AUTHORIZATION="Token invalid")
        self.assertEqual(client.get("/api/tasks/").status_code, 401)

    def test_session_api_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.asha, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(client.get("/api/tasks/").status_code, 200)
        self.assertEqual(client.post("/api/tasks/", {"title": "Needs CSRF"}).status_code, 403)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DemoSeedTests(TestCase):
    def test_seed_refuses_production(self):
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command(
                "seed_demo", username="asha", password="Strong-demo-only-739!", stdout=io.StringIO()
            )

    @override_settings(DEBUG=True)
    def test_seed_requires_explicit_password(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(CommandError):
            call_command("seed_demo", username="asha", stdout=io.StringIO())

    @override_settings(DEBUG=True)
    def test_seed_is_idempotent_and_preserves_existing_data(self):
        from entries.models import Entry

        kwargs = {"username": "asha", "password": "Strong-demo-only-739!", "stdout": io.StringIO()}
        call_command("seed_demo", **kwargs)
        entry = Entry.objects.get(key="project_name")
        entry.value = "My renamed workspace"
        entry.save()
        call_command("seed_demo", **kwargs)
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(Entry.objects.count(), 3)
        entry.refresh_from_db()
        self.assertEqual(entry.value, "My renamed workspace")
        with self.assertRaises(CommandError):
            call_command(
                "seed_demo",
                username="asha",
                password="Different-strong-pass-42!",
                stdout=io.StringIO(),
            )

    @override_settings(DEBUG=True)
    def test_seed_accepts_environment_password(self):
        with patch.dict("os.environ", {"DEMO_PASSWORD": "Strong-demo-only-739!"}):
            call_command("seed_demo", username="asha", stdout=io.StringIO())
        self.assertTrue(
            get_user_model().objects.get(username="asha").check_password("Strong-demo-only-739!")
        )
