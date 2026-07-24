from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny
from django.views.generic import ListView, DetailView
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .forms import CourseForm, LessonForm


class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

class LessonListCreateView(ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [AllowAny]

class LessonRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [AllowAny]


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