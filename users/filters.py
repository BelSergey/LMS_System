import django_filters

from .models import Payment


class PaymentFilter(django_filters.FilterSet):
    course = django_filters.NumberFilter(field_name='paid_course_id')
    lesson = django_filters.NumberFilter(field_name='paid_lesson_id')
    payment_method = django_filters.ChoiceFilter(field_name='payment_method',
                                                 choices = Payment.PAYMENT_METHOD_CHOICES)

    class Meta:
        model = Payment
        fields = '__all__'
