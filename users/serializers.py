from  rest_framework import serializers
from .models import User, Payment

from lms.models import Course, Lesson
from  lms.serializers import CourseSerializer, LessonSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'city', 'avatar']
        read_only_fields = ['id']


class PaymentSerializer(serializers.ModelSerializer):
    paid_course = CourseSerializer(read_only=True)
    paid_lesson = LessonSerializer(read_only=True)
    paid_course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(),
                                                        source='paid_course',
                                                        write_only=True,
                                                        required=False,
                                                        allow_null=True)
    paid_lesson_id = serializers.PrimaryKeyRelatedField(queryset=Lesson.objects.all(),
                                                        source='paid_lesson',
                                                        write_only=True,
                                                        required=False,
                                                        allow_null=True)

    class Meta:
        model = Payment
        fields = ['id', 'user', 'payment_date', 'paid_course', 'paid_lesson',
                  'paid_course_id', 'paid_lesson_id', 'amount', 'payment_method']


class UserProfileSerializer(UserSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        fields = UserSerializer.Meta.fields + ['payments']