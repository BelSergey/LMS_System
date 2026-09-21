from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from users.models import User


class UserAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="me@example.com", password="pass12345", is_active=True
        )
        self.other = User.objects.create_user(
            email="other@example.com", password="pass12345", is_active=True
        )

    def test_registration_is_open(self):
        response = self.client.post(
            reverse("users:user-list"),
            {
                "email": "brandnew@example.com",
                "password": "pass12345",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_own_profile_has_full_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("users:user-detail", kwargs={"id": self.user.id})
        )
        self.assertIn("payments", response.data)

    def test_other_profile_is_public_only(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("users:user-detail", kwargs={"id": self.other.id})
        )
        self.assertNotIn("payments", response.data)
        self.assertNotIn("last_name", response.data)

    def test_cannot_edit_other_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("users:user-detail", kwargs={"id": self.other.id}),
            {"first_name": "Hack"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
