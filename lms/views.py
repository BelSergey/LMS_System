from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers as drf_serializers

from drf_spectacular.utils import extend_schema, inline_serializer

from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from users.models import Subscription

from .forms import CourseForm, LessonForm
from .permissions import IsOwner, IsModerator
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer
from .paginators import CoursePagination, LessonPagination

from .tasks import send_course_update_notification


class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = CoursePagination

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), (~IsModerator)()]
        elif self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), (IsOwner | IsModerator)()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), (~IsModerator)(), (IsOwner)()]
        return super().get_permissions()

    def get_queryset(self):
        return Course.objects.filter()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        previous_updated_at = self.get_object().updated_at
        updated_recently = (
                timezone.now() - previous_updated_at < timedelta(hours=4)
        )

        course = serializer.save()

        if not updated_recently:
            transaction.on_commit(
                lambda: send_course_update_notification.delay(
                    course.pk,
                    course.title,
                )
            )


@extend_schema(
    request=inline_serializer(
        name='SubscriptionRequest',
        fields={'course_id': drf_serializers.IntegerField()},
    ),
    responses=inline_serializer(
        name='SubscriptionResponse',
        fields={'message': drf_serializers.CharField()},
    ),
    description='Подписка/отписка от обновлений курса (toggle: если подписки нет — создаёт, если есть — удаляет).',
)
class SubscriptionAPIView(APIView):
    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get('course_id')
        course_item = get_object_or_404(Course, pk=course_id)

        subs_item = Subscription.objects.filter(user=user, course=course_item)

        if subs_item.exists():
            subs_item.delete()
            message = 'подписка удалена'
        else:
            Subscription.objects.create(user=user, course=course_item)
            message = 'подписка добавлена'

        return Response({'message': message})


class LessonListCreateView(ListCreateAPIView):
    serializer_class = LessonSerializer
    pagination_class = LessonPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), (~IsModerator)()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Lesson.objects.none()
        if user.groups.filter(name='moderators').exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LessonRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    serializer_class = LessonSerializer
    queryset = Lesson.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), (IsOwner | IsModerator)()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [IsAuthenticated(), (IsOwner | IsModerator)()]
        elif self.request.method == 'DELETE':
            return [IsAuthenticated(), (IsOwner)()]
        return super().get_permissions()

    def perform_update(self, serializer):
        course = self.get_object().course
        previous_updated_at = course.updated_at
        updated_recently = (
                timezone.now() - previous_updated_at < timedelta(hours=4)
        )
        lesson = serializer.save()
        if not updated_recently:
            transaction.on_commit(
                lambda: send_course_update_notification.delay(
                lesson.course.pk,
                lesson.course.title,
            )
        )


class CourseListView(ListView):
    model = Course
    template_name = 'lms/course_list.html'
    context_object_name = 'courses'


class LessonListView(ListView):
    model = Lesson
    template_name = 'lms/lesson_list.html'
    context_object_name = 'lessons'


class CourseDetailView(DetailView):
    model = Course
    template_name = 'lms/course_detail.html'
    context_object_name = 'course'


class LessonDetailView(DetailView):
    model = Lesson
    template_name = 'lms/lesson_detail.html'
    context_object_name = 'lesson'


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class CourseCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'lms/course_form.html'
    success_url = reverse_lazy('lms:course_list')


class CourseUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'lms/course_form.html'
    success_url = reverse_lazy('lms:course_list')


class CourseDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Course
    template_name = 'lms/course_confirm_delete.html'
    success_url = reverse_lazy('lms:course_list')


class LessonCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'lms/lesson_form.html'
    success_url = reverse_lazy('lms:lesson_list')


class LessonUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'lms/lesson_form.html'
    success_url = reverse_lazy('lms:lesson_list')


class LessonDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Lesson
    template_name = 'lms/lesson_confirm_delete.html'
    success_url = reverse_lazy('lms:lesson_list')
