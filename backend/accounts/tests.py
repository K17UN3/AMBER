import os
from importlib import reload
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


User = get_user_model()


class SettingsTests(SimpleTestCase):
    def test_vercel_frontend_defaults_are_allowed_for_csrf_and_cors(self):
        with patch.dict(os.environ, {"FRONTEND_ORIGIN": "https://amber-app.vercel.app"}, clear=False):
            import config.settings as settings_module

            reloaded_settings = reload(settings_module)

            self.assertIn("https://amber-app.vercel.app", reloaded_settings.CORS_ALLOWED_ORIGINS)
            self.assertIn(r"^https://.*\.vercel\.app$", reloaded_settings.CORS_ALLOWED_ORIGIN_REGEXES)
            self.assertIn("https://amber-app.vercel.app", reloaded_settings.CSRF_TRUSTED_ORIGINS)
            self.assertIn("https://*.vercel.app", reloaded_settings.CSRF_TRUSTED_ORIGINS)


@override_settings(ROOT_URLCONF="config.urls")
class AuthApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def _csrf_token(self):
        response = self.client.get(reverse("auth-csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.data)
        return response.data["csrfToken"]

    def test_csrf_endpoint_returns_token_and_sets_cookie(self):
        response = self.client.get(reverse("auth-csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.data)
        self.assertIn("csrftoken", response.cookies)

    def test_user_endpoint_sets_csrf_cookie_when_anonymous(self):
        response = self.client.get(reverse("auth-user"))

        self.assertEqual(response.status_code, 403)
        self.assertIn("csrftoken", response.cookies)

    def test_register_requires_csrf_and_hashes_password(self):
        response = self.client.post(
            reverse("auth-register"),
            {"username": "alice", "email": "alice@example.com", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        token = self._csrf_token()
        response = self.client.post(
            reverse("auth-register"),
            {"username": "alice", "email": "alice@example.com", "password": "StrongPass123"},
            HTTP_X_CSRFTOKEN=token,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        user = User.objects.get(username="alice")
        self.assertTrue(user.check_password("StrongPass123"))

    def test_register_rejects_duplicate_username_and_email(self):
        User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123",
        )
        token = self._csrf_token()

        response = self.client.post(
            reverse("auth-register"),
            {"username": "alice", "email": "ALICE@example.com", "password": "StrongPass123"},
            HTTP_X_CSRFTOKEN=token,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)
        self.assertIn("email", response.data)

    def test_login_user_and_logout_flow(self):
        User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123",
        )
        token = self._csrf_token()

        login_response = self.client.post(
            reverse("auth-login"),
            {"username": "alice", "password": "StrongPass123"},
            HTTP_X_CSRFTOKEN=token,
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("sessionid", login_response.cookies)

        user_response = self.client.get(reverse("auth-user"))
        self.assertEqual(user_response.status_code, 200)
        self.assertEqual(user_response.data["username"], "alice")

        logout_response = self.client.post(
            reverse("auth-logout"),
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(logout_response.status_code, 204)

        user_response = self.client.get(reverse("auth-user"))
        self.assertEqual(user_response.status_code, 403)

    def test_login_accepts_email_address(self):
        User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123",
        )
        token = self._csrf_token()

        response = self.client.post(
            reverse("auth-login"),
            {"username": "ALICE@example.com", "password": "StrongPass123"},
            HTTP_X_CSRFTOKEN=token,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "alice")

    def test_auth_pages_are_available_in_browser(self):
        for url_name in ("auth-user", "auth-register", "auth-login"):
            response = self.client.get(reverse(url_name), HTTP_ACCEPT="text/html")
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/html", response["Content-Type"])

    def test_register_and_login_work_from_html_forms(self):
        response = self.client.get(reverse("auth-register"), HTTP_ACCEPT="text/html")
        token = response.cookies["csrftoken"].value

        response = self.client.post(
            reverse("auth-register"),
            {"username": "alice", "email": "alice@example.com", "password": "StrongPass123"},
            HTTP_ACCEPT="text/html",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("auth-login"))

        response = self.client.post(
            reverse("auth-login"),
            {"username": "alice", "password": "StrongPass123"},
            HTTP_ACCEPT="text/html",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("auth-user"))

        response = self.client.get(reverse("auth-logout"), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
