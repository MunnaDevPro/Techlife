from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()

class DashboardApiViewsTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_superuser(
            email="admin_apidocs@techlifebd.com",
            password="Password123!",
            first_name="Admin",
            last_name="Staff"
        )
        self.normal_user = User.objects.create_user(
            email="user_apidocs@techlifebd.com",
            password="Password123!",
            first_name="Normal",
            last_name="User"
        )

    def test_unauthenticated_user_redirected(self):
        url = reverse("dashboard:api_docs")
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN])

    def test_non_staff_user_denied(self):
        self.client.force_login(self.normal_user)
        url = reverse("dashboard:api_docs")
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN])

    def test_staff_user_can_access_api_docs(self):
        self.client.force_login(self.staff_user)
        url = reverse("dashboard:api_docs")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "API Documentation")

    def test_staff_user_can_access_api_config(self):
        self.client.force_login(self.staff_user)
        url = reverse("dashboard:api_config")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "API Tokens")

    def test_staff_user_can_export_openapi_spec(self):
        self.client.force_login(self.staff_user)
        url = reverse("dashboard:api_export") + "?format=openapi"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertIn("openapi", response.json())

    def test_staff_user_can_export_postman_collection(self):
        self.client.force_login(self.staff_user)
        url = reverse("dashboard:api_export") + "?format=postman"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertIn("info", response.json())

    def test_staff_user_can_export_markdown(self):
        self.client.force_login(self.staff_user)
        url = reverse("dashboard:api_export") + "?format=markdown"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "text/markdown")
        self.assertContains(response, "TechLife REST API Reference")
