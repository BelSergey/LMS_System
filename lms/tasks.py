from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

from users.models import Subscription


@shared_task
def send_course_update_notification(course_id, course_title):
    subscriber_emails = list(
        Subscription.objects.filter(course_id=course_id).values_list(
            "user__email", flat=True
        )
    )
    if not subscriber_emails:
        return "No subscribers to notify"

    send_mail(
        subject=f"Курс «{course_title}» обновлён",
        message=f"Материалы курса «{course_title}» были обновлены. Загляните и проверьте новые материалы!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=subscriber_emails,
        fail_silently=False,
    )
    return f"Notified {len(subscriber_emails)} subscribers"
