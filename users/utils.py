from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .tokens import email_confirmation_token

def send_confirmation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_confirmation_token.make_token(user)
    confirm_url = request.build_absolute_uri(
        reverse_lazy("users:confirm_email", kwargs={"uidb64": uid, "token": token})
    )
    subject = "Подтверждение регистрации"
    body = f"Здравствуйте, {user.first_name or user.email}!\n\nДля подтверждения email перейдите по ссылке:\n{confirm_url}\n"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)