from django.urls import path
from .views import (
    ProfileView, register, confirm_email, EmailLoginView,
    logout_view, UserPasswordResetView, UserPasswordResetDoneView,
    UserPasswordResetConfirmView, UserPasswordResetCompleteView, ProfileUpdateView
)

app_name = 'users'

urlpatterns = [
    path('profile/', ProfileUpdateView.as_view(), name='profile'),
    path('register/', register, name='register'),
    path('confirm/<uidb64>/<token>/', confirm_email, name='confirm_email'),
    path('login/', EmailLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', UserPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', UserPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', UserPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]