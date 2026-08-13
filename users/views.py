from django.contrib.auth import login, logout
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView,
    LoginView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from rest_framework import serializers as drf_serializers
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView


from drf_spectacular.utils import extend_schema, inline_serializer

from .forms import RegisterForm, EmailAuthenticationForm, UserProfileForm
from .models import User, Payment, Subscription
from .serializers import UserProfileSerializer, PaymentSerializer, UserSerializer, RegisterSerializer, PublicUserSerializer
from .tokens import email_confirmation_token
from .filters import PaymentFilter
from .utils import send_confirmation_email
from .permissions import IsProfileOwner
from .services import create_stripe_price, create_stripe_product, create_stripe_checkout_session

from lms.models import Course, Lesson


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_confirmation_email(request, user)
            messages.success(
                request,
                "Регистрация прошла успешно. Проверьте почту и перейдите по ссылке для подтверждения email.",
            )
            return redirect("users:login")
    else:
        form = RegisterForm()
    return render(request, "users/register.html", {"form": form})


def confirm_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None

    if user is not None and email_confirmation_token.check_token(user, token):
        user.is_email_confirmed = True
        user.is_active = True
        user.save(update_fields=["is_email_confirmed", "is_active"])
        messages.success(request, "Email подтверждён. Теперь вы можете войти в систему.")
    else:
        messages.error(request, "Ссылка подтверждения недействительна или устарела.")
    return redirect("users:login")


class EmailLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = EmailAuthenticationForm

    def form_invalid(self, form):
        messages.error(self.request, "Неверный email/пароль, либо email ещё не подтверждён.")
        return super().form_invalid(form)


def logout_view(request):
    logout(request)
    messages.success(request, "Вы вышли из системы.")
    return redirect("users:login")


class UserPasswordResetView(PasswordResetView):
    template_name = "users/password_reset_form.html"
    email_template_name = "users/password_reset_email.html"
    subject_template_name = "users/password_reset_subject.txt"
    success_url = reverse_lazy("users:password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "users/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "users/password_reset_complete.html"

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'users/profile_form.html'
    success_url = reverse_lazy('home')

    def get_object(self, queryset=None):
        return self.request.user

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    lookup_field = 'id'

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsProfileOwner()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        send_confirmation_email(self.request,user)

    @extend_schema(responses=UserProfileSerializer)
    def retrieve(self, request, *args, **kwargs):
       instance = self.get_object()
       if instance == request.user:
           serializer = UserProfileSerializer(instance, context={'request': request})
       else:
           serializer = PublicUserSerializer(instance, context={'request': request})
       return Response(serializer.data)



class PaymentListAPIView(ListAPIView):
        queryset = Payment.objects.select_related('user', 'paid_course', 'paid_lesson').all()
        serializer_class = PaymentSerializer
        permission_classes = [IsAuthenticated]
        filter_backends = [DjangoFilterBackend, OrderingFilter]
        filterset_class = PaymentFilter
        ordering_fields = ['payment_date']
        ordering = ['-payment_date']

@extend_schema(
    request=inline_serializer(
        name='PaymentCreateRequest',
        fields={
            'course_id': drf_serializers.IntegerField(required=False),
            'lesson_id': drf_serializers.IntegerField(required=False),
            'amount': drf_serializers.DecimalField(max_digits=10, decimal_places=2),
        },
    ),
    responses=PaymentSerializer,
    description=(
        'Создаёт платёж: продукт и цену в Stripe, сессию оплаты, '
        'сохраняет ссылку на оплату и возвращает данные платежа.'
    ),
)
class PaymentCreateAPIView(APIView):
    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        course_id = request.data.get('course_id')
        lesson_id = request.data.get('lesson_id')
        amount = request.data.get('amount')

        if not amount:
            return Response({'detail': 'Поле amount обязательно.'}, status=400)

        course = get_object_or_404(Course, pk=course_id) if course_id else None
        lesson = get_object_or_404(Lesson, pk=lesson_id) if lesson_id else None
        if not course and not lesson:
            return Response({'detail': 'Укажите course_id или lesson_id.'}, status=400)

        product_name = course.title if course else lesson.title

        product = create_stripe_product(product_name)
        price = create_stripe_price(product.id, amount)
        session = create_stripe_checkout_session(price.id)

        payment = Payment.objects.create(
            user=request.user,
            payment_date=timezone.now().date(),
            paid_course=course,
            paid_lesson=lesson,
            amount=amount,
            payment_method=Payment.TRANSFER,
            session_id=session.id,
            payment_link=session.url,
        )

        serializer = PaymentSerializer(payment, context={'request': request})
        return Response(serializer.data, status=201)