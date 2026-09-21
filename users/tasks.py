from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone


@shared_task
def block_inactive_users() -> int:
    cutoff = timezone.now() - timedelta(days=30)
    user_model = get_user_model()

    return user_model.objects.filter(
        is_active=True,
        last_login__lt=cutoff,
    ).update(is_active=False)
