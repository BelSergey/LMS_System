from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, LessonListCreateView, LessonRetrieveUpdateDestroyView,
    CourseListView, LessonListView, CourseDetailView, LessonDetailView, CourseCreateView, CourseUpdateView,
    CourseDeleteView, LessonCreateView, LessonUpdateView, LessonDeleteView, SubscriptionAPIView
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')


app_name = 'lms'
urlpatterns = [
    # API
    path('', include(router.urls)),

    path('lessons/', LessonListCreateView.as_view(), name='lesson-list-create'),
    path('lessons/<int:pk>/', LessonRetrieveUpdateDestroyView.as_view(), name='lesson-detail'),

    path('subscribe/', SubscriptionAPIView.as_view(), name='subscription'),

    path('web/courses/', CourseListView.as_view(), name='course_list'),
    path('web/lessons/', LessonListView.as_view(), name='lesson_list'),
    path('web/courses/<int:pk>/', CourseDetailView.as_view(), name='course_detail'),
    path('web/lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson_detail'),
    path('web/courses/create/', CourseCreateView.as_view(), name='course_create'),
    path('web/courses/<int:pk>/update/', CourseUpdateView.as_view(), name='course_update'),
    path('web/courses/<int:pk>/delete/', CourseDeleteView.as_view(), name='course_delete'),
    path('web/lessons/create/', LessonCreateView.as_view(), name='lesson_create'),
    path('web/lessons/<int:pk>/update/', LessonUpdateView.as_view(), name='lesson_update'),
    path('web/lessons/<int:pk>/delete/', LessonDeleteView.as_view(), name='lesson_delete'),
]
