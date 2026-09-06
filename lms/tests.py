from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from users.models import User, Subscription
from lms.models import Course, Lesson


class LessonCRUDTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="pass12345", is_active=True
        )
        self.stranger = User.objects.create_user(
            email="stranger@example.com", password="pass12345", is_active=True
        )
        self.moderator = User.objects.create_user(
            email="moder@example.com", password="pass12345", is_active=True
        )
        moderators_group, _ = Group.objects.get_or_create(name="moderators")
        self.moderator.groups.add(moderators_group)

        self.course = Course.objects.create(
            title="Django", description="...", owner=self.owner
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Models",
            description="...",
            video_url="https://www.youtube.com/watch?v=abc",
            owner=self.owner,
        )

    def test_anonymous_cannot_list_lessons(self):
        response = self.client.get(reverse("lms:lesson-list-create"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_create_lesson(self):
        self.client.force_authenticate(user=self.owner)
        payload = {
            "course": self.course.id,
            "title": "Views",
            "description": "...",
            "video_url": "https://www.youtube.com/watch?v=xyz",
        }
        response = self.client.post(reverse("lms:lesson-list-create"), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["owner"], self.owner.id)

    def test_non_youtube_link_rejected(self):
        self.client.force_authenticate(user=self.owner)
        payload = {
            "course": self.course.id,
            "title": "Bad link",
            "description": "...",
            "video_url": "https://www.udemy.com/course/xyz",
        }
        response = self.client.post(reverse("lms:lesson-list-create"), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("video_url", response.data)

    def test_moderator_can_update_any_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse("lms:lesson-detail", kwargs={"pk": self.lesson.id})
        response = self.client.patch(url, {"title": "Updated by moderator"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_cannot_delete_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse("lms:lesson-detail", kwargs={"pk": self.lesson.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stranger_gets_empty_lesson_list(self):
        # get_queryset() у LessonListCreateView фильтрует по owner для не-модераторов
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse("lms:lesson-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (
            response.data["results"] if "results" in response.data else response.data
        )
        self.assertEqual(len(results), 0)

    def test_stranger_cannot_update_lesson_not_in_their_queryset(self):
        # объект вне отфильтрованного queryset → get_object() даёт 404, а не 403
        self.client.force_authenticate(user=self.stranger)
        url = reverse("lms:lesson-detail", kwargs={"pk": self.lesson.id})
        response = self.client.patch(url, {"title": "Hack"})
        self.assertIn(
            response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )

    def test_owner_can_delete_own_lesson(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("lms:lesson-detail", kwargs={"pk": self.lesson.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class SubscriptionTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sub_user@example.com", password="pass12345", is_active=True
        )
        self.owner = User.objects.create_user(
            email="course_owner@example.com", password="pass12345", is_active=True
        )
        self.course = Course.objects.create(
            title="DRF", description="...", owner=self.owner
        )

    def test_anonymous_cannot_subscribe(self):
        response = self.client.post(
            reverse("lms:subscription"), {"course_id": self.course.id}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_subscribe_then_unsubscribe(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("lms:subscription")

        response = self.client.post(url, {"course_id": self.course.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "подписка добавлена")
        self.assertTrue(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )

        response = self.client.post(url, {"course_id": self.course.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "подписка удалена")
        self.assertFalse(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )

    def test_course_serializer_reflects_subscription(self):
        self.client.force_authenticate(user=self.user)
        Subscription.objects.create(user=self.user, course=self.course)

        response = self.client.get(
            reverse("lms:course-detail", kwargs={"pk": self.course.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_subscribed"])
