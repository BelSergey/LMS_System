from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    register,
    confirm_email,
    EmailLoginView,
    UserViewSet,
    logout_view,
    UserPasswordResetView,
    UserPasswordResetDoneView,
    UserPasswordResetConfirmView,
    UserPasswordResetCompleteView,
    ProfileUpdateView,
    PaymentListAPIView,
    PaymentCreateAPIView,
    PaymentStatusAPIView,
)
from django.urls import include

router = DefaultRouter()
router.register(r"api/users", UserViewSet, basename="user")

app_name = "users"

urlpatterns = [
    path("", include(router.urls)),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
    path("api/payments/", PaymentListAPIView.as_view(), name="payment-list"),
    path("api/payments/create/", PaymentCreateAPIView.as_view(), name="payment-create"),
    path(
        "api/payments/<int:pk>/status/",
        PaymentStatusAPIView.as_view(),
        name="payment-status",
    ),
    path("register/", register, name="register"),
    path("confirm/<uidb64>/<token>/", confirm_email, name="confirm_email"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("password-reset/", UserPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        UserPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        UserPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
