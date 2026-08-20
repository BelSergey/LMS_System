from datetime import timedelta
from django.utils import timezone

from .tasks import send_course_update_notification


def maybe_notify_subscribers(course):

    now = timezone.now()
    if course.last_notified_at and now - course.last_notified_at < timedelta(hours=4):
        return

    send_course_update_notification.delay(course.id, course.title)
    course.last_notified_at = now
    course.save(update_fields=['last_notified_at'])