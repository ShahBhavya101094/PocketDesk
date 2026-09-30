from datetime import timedelta

from axes.models import AccessAttempt
from axes.utils import reset
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

User = get_user_model()
PASSWORD = "Distinct-workshop-password-2026!"


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="asha", password=PASSWORD)

    def test_login_and_post_logout(self):
        response = self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertRedirects(response, "/tasks/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_external_next_is_not_followed(self):
        response = self.client.post(
            reverse("login"),
            {"username": "asha", "password": PASSWORD, "next": "https://attacker.invalid/"},
        )
        self.assertRedirects(response, "/tasks/", fetch_redirect_response=False)

    def test_login_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(
            reverse("login"), {"username": "asha", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 403)

    def test_logout_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")
        self.assertEqual(client.post(reverse("logout")).status_code, 403)

    @override_settings(AXES_FAILURE_LIMIT=3)
    def test_lockout_persists_across_clients_and_blocks_correct_password(self):
        for _ in range(3):
            response = self.client.post(reverse("login"), {"username": "asha", "password": "wrong"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")
        self.assertTrue(AccessAttempt.objects.filter(username="asha").exists())
        fresh_client = Client()
        response = fresh_client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", fresh_client.session)
        reset(username="asha")
        response = fresh_client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    @override_settings(AXES_FAILURE_LIMIT=2)
    def test_browsable_api_login_is_also_protected(self):
        for _ in range(2):
            response = self.client.post(
                "/api-auth/login/", {"username": "asha", "password": "wrong"}
            )
        self.assertEqual(response.status_code, 429)

    @override_settings(AXES_FAILURE_LIMIT=2)
    def test_expired_lockout_allows_login_again(self):
        for _ in range(2):
            self.client.post(reverse("login"), {"username": "asha", "password": "wrong"})
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))
        response = self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_failed_login_does_not_store_password_in_attempt_metadata(self):
        failed_password = "never-store-this-password"
        self.client.post(reverse("login"), {"username": "asha", "password": failed_password})
        attempt = AccessAttempt.objects.get(username="asha")
        self.assertNotIn(failed_password, attempt.post_data)

    def test_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)


class SignupTests(TestCase):
    def payload(self, **extra):
        return {"username": "learner", "password1": PASSWORD, "password2": PASSWORD, **extra}

    @override_settings(PUBLIC_SIGNUP_ENABLED=True)
    def test_signup_uses_password_hash_and_has_no_privileges(self):
        response = self.client.post(
            reverse("signup"), self.payload(is_staff="True", is_superuser="True")
        )
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        user = User.objects.get(username="learner")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(PUBLIC_SIGNUP_ENABLED=False)
    def test_disabled_signup_rejects_get_and_post(self):
        self.assertEqual(self.client.get(reverse("signup")).status_code, 404)
        self.assertEqual(self.client.post(reverse("signup"), self.payload()).status_code, 404)
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse("signup"), self.payload(password1="123", password2="123")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertTrue(response.context["form"].errors["password2"])

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username="learner", password=PASSWORD)
        response = self.client.post(reverse("signup"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_signup_requires_csrf(self):
        self.assertEqual(
            Client(enforce_csrf_checks=True).post(reverse("signup"), self.payload()).status_code,
            403,
        )
