from django.urls import path
from .views import (
    RegisterView, ProfileView, CustomTokenObtainPairView, VerifyOTPView,
    ForgotPasswordView, VerifyForgotPasswordOTPView, ChangePasswordView,
    UserCompleteProfileView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/<int:user_id>/details/', UserCompleteProfileView.as_view(), name='user_complete_profile'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-forgot-password-otp/', VerifyForgotPasswordOTPView.as_view(), name='verify_forgot_password_otp'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]