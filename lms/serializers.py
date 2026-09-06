
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Course, Lesson
from .validators import YoutubeLinkValidator


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        validators = [YoutubeLinkValidator(field='video_url')]


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'preview', 'description', 'lessons_count', 'lessons', 'is_subscribed']
    @extend_schema_field(serializers.IntegerField)
    def get_lessons_count(self, obj):
        return obj.lessons.count()
    @extend_schema_field(serializers.BooleanField)
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        return obj.subscriptions.filter(user=user).exists()
