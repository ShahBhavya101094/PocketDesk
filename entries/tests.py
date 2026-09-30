from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .forms import EntryForm
from .models import Entry
from .serializers import EntrySerializer
from .views import _save_form


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.asha = get_user_model().objects.create_user("asha", password="test-pass")
        cls.other = get_user_model().objects.create_user("other", password="test-pass")
        cls.entry = Entry.objects.create(
            owner=cls.asha, key="course_link", value="https://docs.djangoproject.com/en/5.2/"
        )
        cls.private = Entry.objects.create(
            owner=cls.other, key="private_note", value="Only the other account may see this"
        )

    def setUp(self):
        self.client.force_login(self.asha, backend="django.contrib.auth.backends.ModelBackend")
        self.api = APIClient()
        self.api.force_authenticate(self.asha)

    def test_form_normalizes_and_has_no_owner_field(self):
        form = EntryForm(
            {"key": "  PROJECT_Name  ", "value": "  PocketDesk  ", "owner": self.other.pk},
            user=self.asha,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["key"], "project_name")
        self.assertEqual(form.cleaned_data["value"], "PocketDesk")
        self.assertNotIn("owner", form.fields)

    def test_invalid_keys_rejected_by_form_and_api(self):
        for key in ["", " ", "bad key", "slash/key", "dot.key", "café", "k" * 81]:
            with self.subTest(key=key):
                self.assertFalse(
                    EntryForm({"key": key, "value": "A value"}, user=self.asha).is_valid()
                )
                self.assertEqual(
                    self.api.post("/api/entries/", {"key": key, "value": "A value"}).status_code,
                    400,
                )

    def test_values_reject_blank_and_over_limit(self):
        for value in ["", "   ", "x" * 5001]:
            with self.subTest(length=len(value)):
                self.assertFalse(
                    EntryForm({"key": "new_key", "value": value}, user=self.asha).is_valid()
                )
                self.assertEqual(
                    self.api.post("/api/entries/", {"key": "new_key", "value": value}).status_code,
                    400,
                )
        self.assertTrue(
            EntryForm(
                {"key": "valid-80_" + "k" * 71, "value": "x" * 5000}, user=self.asha
            ).is_valid()
        )

    def test_model_validation_normalizes_fields(self):
        entry = Entry(owner=self.asha, key="  SOME_Key  ", value="  text  ")
        entry.full_clean()
        self.assertEqual(entry.key, "some_key")
        self.assertEqual(entry.value, "text")
        entry.key = "bad.key"
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_database_enforces_owner_key_uniqueness(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Entry.objects.create(owner=self.asha, key="course_link", value="Duplicate")
        self.assertEqual(Entry.objects.filter(owner=self.asha, key="course_link").count(), 1)
        Entry.objects.create(
            owner=self.other, key="course_link", value="Same key, different account"
        )

    def test_form_checks_normalized_duplicates_and_allows_own_update(self):
        self.assertFalse(
            EntryForm({"key": " COURSE_LINK ", "value": "Duplicate"}, user=self.asha).is_valid()
        )
        self.assertTrue(
            EntryForm(
                {"key": "course_link", "value": "Updated"}, user=self.asha, instance=self.entry
            ).is_valid()
        )
        self.assertTrue(
            EntryForm({"key": "course_link", "value": "Other account"}, user=self.other).is_valid()
        )

    def test_html_authentication_and_scoped_list(self):
        response = self.client.get(reverse("entries:list"))
        self.assertContains(response, "course_link")
        self.assertNotContains(response, "private_note")
        self.assertEqual(response.context["total_count"], 1)
        self.client.logout()
        for route, kwargs in [
            ("list", {}),
            ("create", {}),
            ("update", {"pk": self.entry.pk}),
            ("delete", {"pk": self.entry.pk}),
        ]:
            self.assertEqual(
                self.client.get(reverse(f"entries:{route}", kwargs=kwargs)).status_code, 302
            )

    def test_html_search_and_pagination(self):
        Entry.objects.bulk_create(
            [Entry(owner=self.asha, key=f"note_{n:02}", value="Study notes") for n in range(12)]
        )
        response = self.client.get(reverse("entries:list"), {"q": "Study", "page": "invalid"})
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertEqual(response.context["page_obj"].paginator.count, 12)
        self.assertEqual(response.context["query"], "Study")

    def test_html_create_update_delete(self):
        response = self.client.post(
            reverse("entries:create"),
            {"key": "PROJECT_name", "value": "PocketDesk", "owner": self.other.pk},
        )
        self.assertRedirects(response, reverse("entries:list"))
        entry = Entry.objects.get(key="project_name")
        self.assertEqual(entry.owner, self.asha)
        self.client.post(
            reverse("entries:update", args=[entry.pk]),
            {"key": "project_name", "value": "My project", "owner": self.other.pk},
        )
        entry.refresh_from_db()
        self.assertEqual(entry.value, "My project")
        self.assertEqual(entry.owner, self.asha)
        self.assertEqual(
            self.client.get(reverse("entries:delete", args=[entry.pk])).status_code, 200
        )
        self.assertTrue(Entry.objects.filter(pk=entry.pk).exists())
        self.assertEqual(
            self.client.post(reverse("entries:delete", args=[entry.pk])).status_code, 302
        )
        self.assertFalse(Entry.objects.filter(pk=entry.pk).exists())

    def test_html_other_users_records_are_inaccessible(self):
        for route in ["update", "delete"]:
            url = reverse(f"entries:{route}", args=[self.private.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(
                self.client.post(url, {"key": "renamed", "value": "Changed"}).status_code, 404
            )
        self.private.refresh_from_db()
        self.assertEqual(self.private.key, "private_note")

    def test_html_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.asha, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(
            client.post(
                reverse("entries:create"), {"key": "new", "value": "Not authorized"}
            ).status_code,
            403,
        )
        self.assertEqual(
            client.post(reverse("entries:delete", args=[self.entry.pk])).status_code, 403
        )

    def test_html_escapes_values(self):
        Entry.objects.create(
            owner=self.asha, key="unsafe_markup", value='<script>alert("x")</script>'
        )
        response = self.client.get(reverse("entries:list"))
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_form_handles_duplicate_created_after_validation(self):
        form = EntryForm({"key": "race_key", "value": "First request"}, user=self.asha)
        self.assertTrue(form.is_valid())
        # Simulate the other request committing after this form passed validation.
        Entry.objects.create(owner=self.asha, key="race_key", value="Other request won")
        self.assertFalse(_save_form(form, self.asha))
        self.assertIn("key", form.errors)
        self.assertEqual(
            Entry.objects.get(owner=self.asha, key="race_key").value, "Other request won"
        )

    def test_api_authentication_and_scoped_pagination(self):
        self.assertEqual(APIClient().get("/api/entries/").status_code, 401)
        response = self.api.get("/api/entries/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["key"], "course_link")
        self.assertNotIn("owner", response.data["results"][0])

    def test_api_pagination_counts_only_owned_records(self):
        Entry.objects.bulk_create(
            [Entry(owner=self.asha, key=f"owned_{n}", value="A note") for n in range(10)]
        )
        Entry.objects.bulk_create(
            [Entry(owner=self.other, key=f"foreign_{n}", value="Private") for n in range(12)]
        )
        response = self.api.get("/api/entries/")
        self.assertEqual(response.data["count"], 11)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        second = self.api.get(response.data["next"])
        self.assertEqual(len(second.data["results"]), 1)
        self.assertIsNone(second.data["next"])
        ids = [row["id"] for row in response.data["results"] + second.data["results"]]
        self.assertEqual(Entry.objects.filter(id__in=ids, owner=self.asha).count(), 11)

    def test_api_create_and_patch_ignore_owner_forgery(self):
        response = self.api.post(
            "/api/entries/",
            {"key": "  PROJECT_Name  ", "value": "PocketDesk", "owner": self.other.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        entry = Entry.objects.get(pk=response.data["id"])
        self.assertEqual(entry.key, "project_name")
        self.assertEqual(entry.owner, self.asha)
        response = self.api.patch(
            f"/api/entries/{entry.pk}/",
            {"value": "  Updated  ", "owner": self.other.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.value, "Updated")
        self.assertEqual(entry.key, "project_name")
        self.assertEqual(entry.owner, self.asha)

    def test_api_duplicate_create_and_rename_rejected(self):
        self.assertEqual(
            self.api.post(
                "/api/entries/", {"key": "COURSE_LINK", "value": "Duplicate"}
            ).status_code,
            400,
        )
        entry = Entry.objects.create(owner=self.asha, key="another", value="Keep this")
        self.assertEqual(
            self.api.patch(f"/api/entries/{entry.pk}/", {"key": "course_link"}).status_code, 400
        )
        entry.refresh_from_db()
        self.assertEqual(entry.key, "another")

    def test_api_other_account_can_use_same_key(self):
        self.api.force_authenticate(self.other)
        self.assertEqual(
            self.api.post(
                "/api/entries/", {"key": "course_link", "value": "Different owner"}
            ).status_code,
            201,
        )

    def test_api_foreign_records_return_404(self):
        url = f"/api/entries/{self.private.pk}/"
        self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.patch(url, {"value": "Changed"}).status_code, 404)
        self.assertEqual(self.api.delete(url).status_code, 404)
        self.assertEqual(
            self.api.get("/api/entries/by-key/", {"key": "private_note"}).status_code, 404
        )

    def test_api_lookup_by_key_and_invalid_key(self):
        response = self.api.get("/api/entries/by-key/", {"key": " COURSE_LINK "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.entry.pk)
        self.assertEqual(self.api.get("/api/entries/by-key/").status_code, 400)
        self.assertEqual(self.api.get("/api/entries/by-key/", {"key": "missing"}).status_code, 404)

    def test_api_search_and_ordering(self):
        Entry.objects.create(owner=self.asha, key="project_name", value="PocketDesk")
        response = self.api.get("/api/entries/", {"search": "PocketDesk", "ordering": "-key"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["key"], "project_name")

    def test_api_delete(self):
        self.assertEqual(self.api.delete(f"/api/entries/{self.entry.pk}/").status_code, 204)
        self.assertFalse(Entry.objects.filter(pk=self.entry.pk).exists())

    def test_api_database_constraint_is_a_graceful_400(self):
        # Bypass the pre-check to simulate a duplicate arriving between validation
        # and save. Exercise the real database constraint and savepoint recovery.
        with patch.object(EntrySerializer, "validate", lambda serializer, attrs: attrs):
            response = self.api.post(
                "/api/entries/", {"key": "course_link", "value": "Concurrent duplicate"}
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("key", response.data)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.value, "https://docs.djangoproject.com/en/5.2/")

    def test_api_database_constraint_handles_concurrent_rename(self):
        entry = Entry.objects.create(owner=self.asha, key="other_key", value="Keep this")
        with patch.object(EntrySerializer, "validate", lambda serializer, attrs: attrs):
            response = self.api.patch(f"/api/entries/{entry.pk}/", {"key": "course_link"})
        self.assertEqual(response.status_code, 400)
        entry.refresh_from_db()
        self.assertEqual(entry.key, "other_key")

    def test_owner_deletion_cascades(self):
        self.asha.delete()
        self.assertFalse(Entry.objects.filter(pk=self.entry.pk).exists())
        self.assertTrue(Entry.objects.filter(pk=self.private.pk).exists())
