from django import forms
from .models import Course, Lesson


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "preview", "description"]


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["course", "title", "description", "preview", "video_url"]
