from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import User


@shared_task
def deactivate_inactive_users():
    cutoff = timezone.now() - timedelta(days=30)
    users = User.objects.filter(last_login__lt=cutoff, is_active=True)
    count = users.update(is_active=False)
    return f'Deactivated {count} users'