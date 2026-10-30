from django.test import Client, TestCase
from django.urls import reverse

from .models import Role, User

PASSWORD = "Sealtrack-local-2026"


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.csrf_client = Client(enforce_csrf_checks=True)

    def signup(self, client=None, **overrides):
        payload = {"full_name": "Asha Rao", "email": "asha@example.com", "password": PASSWORD, **overrides}
        return (client or self.client).post("/api/auth/signup/", payload, content_type="application/json")

    def test_signup_creates_site_manager_and_signs_in(self):
        response = self.signup()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], Role.SITE_MANAGER)
        self.assertEqual(response.json()["email"], "asha@example.com")
        self.assertFalse(response.json()["is_staff"])
        self.assertEqual(self.client.get("/api/auth/me/").json()["email"], "asha@example.com")

    def test_signup_normalises_email(self):
        self.signup(email="  Asha@Example.COM ")
        self.assertTrue(User.objects.filter(email="asha@example.com").exists())

    def test_signup_rejects_duplicate_email_case_insensitively(self):
        self.signup()
        response = self.signup(email="ASHA@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_signup_rejects_weak_password(self):
        response = self.signup(password="123")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())

    def test_signup_cannot_choose_a_role(self):
        self.signup(role=Role.SUPER_ADMIN)
        self.assertEqual(User.objects.get(email="asha@example.com").role, Role.SITE_MANAGER)

    def test_login_success_and_me(self):
        self.signup()
        self.client.post("/api/auth/logout/")
        response = self.client.post("/api/auth/login/", {"email": "asha@example.com", "password": PASSWORD}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_login_wrong_password_and_unknown_email_look_identical(self):
        self.signup()
        self.client.post("/api/auth/logout/")
        wrong = self.client.post("/api/auth/login/", {"email": "asha@example.com", "password": "nope-nope"}, content_type="application/json")
        unknown = self.client.post("/api/auth/login/", {"email": "ghost@example.com", "password": "nope-nope"}, content_type="application/json")
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.json(), unknown.json())

    def test_disabled_user_cannot_log_in(self):
        self.signup()
        User.objects.filter(email="asha@example.com").update(is_active=False)
        self.client.post("/api/auth/logout/")
        response = self.client.post("/api/auth/login/", {"email": "asha@example.com", "password": PASSWORD}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_me_requires_sign_in(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)

    def test_logout_ends_the_session(self):
        self.signup()
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)

    def test_posts_without_csrf_token_are_rejected(self):
        # Browsers send cross-site POSTs with cookies; the CSRF token is what stops them.
        response = self.csrf_client.post("/api/auth/login/", {"email": "a@b.com", "password": "x"}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_signup_with_csrf_token_succeeds(self):
        self.csrf_client.get("/api/auth/csrf/")
        token = self.csrf_client.cookies["csrftoken"].value
        response = self.csrf_client.post(
            "/api/auth/signup/",
            {"full_name": "Asha Rao", "email": "asha@example.com", "password": PASSWORD},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 201)

    def test_health_is_public(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.json(), {"status": "ok", "service": "sealtrack-api"})


class AdminLoginTests(TestCase):
    def test_superuser_can_sign_in_to_django_admin(self):
        User.objects.create_superuser(email="root@example.com", full_name="Root", password=PASSWORD)
        client = Client()
        response = client.post(reverse("admin:login"), {"username": "root@example.com", "password": PASSWORD, "next": "/admin/"})
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(client.get("/admin/").status_code, 200)

    def test_site_manager_cannot_use_django_admin(self):
        User.objects.create_user(email="sm@example.com", full_name="SM", password=PASSWORD)
        client = Client()
        response = client.post(reverse("admin:login"), {"username": "sm@example.com", "password": PASSWORD, "next": "/admin/"})
        self.assertEqual(response.status_code, 200)  # stays on the login form
        self.assertEqual(client.get("/admin/").status_code, 302)

    def test_superuser_gets_super_admin_role(self):
        user = User.objects.create_superuser(email="root@example.com", full_name="Root", password=PASSWORD)
        self.assertEqual(user.role, Role.SUPER_ADMIN)
        self.assertTrue(user.is_staff and user.is_superuser)


class UserManagementApiTests(TestCase):
    """Tests for GET/POST /api/accounts/users/ and PATCH /api/accounts/users/{id}/."""

    def setUp(self):
        self.super_admin = User.objects.create_superuser(email="super@example.com", full_name="Super Admin", password=PASSWORD)
        self.admin = User.objects.create_user(email="admin@example.com", full_name="Admin User", password=PASSWORD, role=Role.ADMIN, is_staff=True)
        self.sm = User.objects.create_user(email="sm@example.com", full_name="Site Manager", password=PASSWORD)

        self.super_client = Client()
        self.super_client.post("/api/auth/login/", {"email": "super@example.com", "password": PASSWORD}, content_type="application/json")

        self.admin_client = Client()
        self.admin_client.post("/api/auth/login/", {"email": "admin@example.com", "password": PASSWORD}, content_type="application/json")

        self.sm_client = Client()
        self.sm_client.post("/api/auth/login/", {"email": "sm@example.com", "password": PASSWORD}, content_type="application/json")

    def test_super_admin_can_list_users(self):
        response = self.super_client.get("/api/accounts/users/")
        self.assertEqual(response.status_code, 200)
        emails = [u["email"] for u in response.json()]
        self.assertIn("super@example.com", emails)
        self.assertIn("sm@example.com", emails)

    def test_admin_can_list_users(self):
        response = self.admin_client.get("/api/accounts/users/")
        self.assertEqual(response.status_code, 200)

    def test_site_manager_cannot_list_users(self):
        response = self.sm_client.get("/api/accounts/users/")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_list_users(self):
        response = Client().get("/api/accounts/users/")
        self.assertEqual(response.status_code, 403)

    def test_user_list_response_includes_profile_fields(self):
        response = self.super_client.get("/api/accounts/users/")
        user = next(u for u in response.json() if u["email"] == "sm@example.com")
        self.assertIn("phone", user)
        self.assertIn("employee_id", user)
        self.assertIn("designation", user)
        self.assertIn("first_login_completed", user)

    def test_super_admin_can_create_site_manager(self):
        payload = {"full_name": "New SM", "email": "newsm@example.com", "password": PASSWORD, "role": Role.SITE_MANAGER}
        response = self.super_client.post("/api/accounts/users/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], Role.SITE_MANAGER)

    def test_admin_can_create_site_manager(self):
        payload = {"full_name": "Another SM", "email": "anothersm@example.com", "password": PASSWORD, "role": Role.SITE_MANAGER}
        response = self.admin_client.post("/api/accounts/users/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)

    def test_admin_cannot_create_admin_role(self):
        payload = {"full_name": "New Admin", "email": "newadmin@example.com", "password": PASSWORD, "role": Role.ADMIN}
        response = self.admin_client.post("/api/accounts/users/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_create_admin_role(self):
        payload = {"full_name": "New Admin", "email": "newadmin@example.com", "password": PASSWORD, "role": Role.ADMIN}
        response = self.super_client.post("/api/accounts/users/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], Role.ADMIN)

    def test_duplicate_email_rejected_on_create(self):
        payload = {"full_name": "Dup", "email": "sm@example.com", "password": PASSWORD, "role": Role.SITE_MANAGER}
        response = self.super_client.post("/api/accounts/users/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_super_admin_can_patch_user(self):
        response = self.super_client.patch(
            f"/api/accounts/users/{self.sm.pk}/",
            {"phone": "9876543210", "designation": "Site Engineer"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.sm.refresh_from_db()
        self.assertEqual(self.sm.phone, "9876543210")
        self.assertEqual(self.sm.designation, "Site Engineer")

    def test_admin_cannot_patch_another_admin(self):
        response = self.admin_client.patch(
            f"/api/accounts/users/{self.super_admin.pk}/",
            {"designation": "Try"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_disable_user_via_patch(self):
        response = self.super_client.patch(
            f"/api/accounts/users/{self.sm.pk}/",
            {"is_active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.sm.refresh_from_db()
        self.assertFalse(self.sm.is_active)
