from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (UserRegistrationSerializer, UserProfileSerializer, 
                          UserLoginSerializer, ForgotPasswordSerializer, VerifyForgotPasswordOTPSerializer, 
                          ChangePasswordSerializer)
from .models import User
from rides.models import Ride
from rides.serializers import RideSerializer
from reviews.models import Review, Badge
from reviews.serializers import ReviewSerializer, BadgeSerializer, SimplifiedUserSerializer
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction
from django.db.models import Q
import random
import os

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if User.objects.filter(email=email).exists():
                return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

            otp_code = str(random.randint(100000, 999999))
            cache.set(f"pending_user_{email}", serializer.validated_data, timeout=300)
            cache.set(f"otp_{email}", otp_code, timeout=300)

            send_mail(
                subject="Your OTP for RideSafeNSU Registration",
                message=f"Your OTP is {otp_code}. It expires in 5 minutes.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"message": "OTP sent to your email. Please verify within 5 minutes."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp_code = request.data.get("otp_code")
        expo_push_token = request.data.get("expo_push_token")  # Add this

        if not email or not otp_code:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        stored_otp = cache.get(f"otp_{email}")
        user_data = cache.get(f"pending_user_{email}")

        if not stored_otp or not user_data:
            return Response({"error": "OTP expired or invalid request."}, status=status.HTTP_400_BAD_REQUEST)

        if stored_otp != otp_code:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            gender=user_data['gender'],
            student_id=user_data['student_id'],
            phone_number=user_data.get('phone_number', ''),
            password=user_data['password']
        )
        if 'profile_photo' in user_data:
            user.profile_photo = user_data['profile_photo']
        if expo_push_token:  # Save the token during registration
            user.expo_push_token = expo_push_token
        user.save()

        refresh = RefreshToken.for_user(user)
        user_data_serialized = UserProfileSerializer(user).data
        response_data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user_data_serialized
        }

        cache.delete(f"otp_{email}")
        cache.delete(f"pending_user_{email}")

        return Response(response_data, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            expo_push_token = serializer.validated_data.get('expo_push_token')  # Add this
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                if expo_push_token and user.expo_push_token != expo_push_token:  # Update token if changed
                    user.expo_push_token = expo_push_token
                    user.save()
                refresh = RefreshToken.for_user(user)
                user_data = UserProfileSerializer(user).data
                response_data = {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": user_data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserCompleteProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            # Get the user with prefetching related data for optimization
            user = get_object_or_404(
                User.objects.prefetch_related(
                    'hosted_rides',
                    'ride_members',
                    'received_reviews',
                    'badge'
                ),
                id=user_id
            )

            # Basic user profile data
            user_profile_serializer = UserProfileSerializer(user)

            # Ride history (both hosted and joined rides)
            ride_history = Ride.objects.filter(
                Q(host=user) | Q(members=user),
                is_completed=True
            ).distinct().order_by('-departure_time')
            ride_history_serializer = RideSerializer(ride_history, many=True)

            # User reviews
            reviews = Review.objects.filter(reviewed_user=user).select_related('reviewer', 'ride')
            review_serializer = ReviewSerializer(reviews, many=True)

            # Badge status
            badge, created = Badge.objects.get_or_create(user=user)
            if created or not badge.level:
                badge.update_badge()
            badge_serializer = BadgeSerializer(badge)

            # Combine all data into a single response
            response_data = {
                "user": {
                    **user_profile_serializer.data,
                    "badge": badge_serializer.data,
                    "ride_history": ride_history_serializer.data,
                    "reviews": review_serializer.data,
                    "total_completed_rides": ride_history.count(),
                    "average_rating": badge.get_average_rating(),
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve user profile: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():  # Ensure atomicity for profile photo update
                # Update name fields if provided
                if 'first_name' in request.data:
                    request.user.first_name = request.data['first_name']
                if 'last_name' in request.data:
                    request.user.last_name = request.data['last_name']

                # Handle profile photo upload with custom naming
                if 'profile_photo' in request.FILES:
                    user = request.user
                    # Define the new filename: <user_id>_user_dp.png
                    new_filename = f"{user.id}_user_dp.png"
                    file_extension = request.FILES['profile_photo'].name.split('.')[-1]  # Preserve extension if not PNG
                    if file_extension.lower() != 'png':
                        new_filename = f"{user.id}_user_dp.{file_extension.lower()}"

                    # Full path for the new file
                    new_file_path = os.path.join(settings.MEDIA_ROOT, 'profiles', new_filename)

                    # Remove old profile photo if it exists and is different
                    if user.profile_photo and os.path.exists(user.profile_photo.path):
                        os.remove(user.profile_photo.path)

                    # Save the new file
                    with open(new_file_path, 'wb+') as destination:
                        for chunk in request.FILES['profile_photo'].chunks():
                            destination.write(chunk)

                    # Update the user's profile_photo field with the relative path
                    user.profile_photo = os.path.join('profiles', new_filename)

                # Save all changes
                user.save()
                serializer = UserProfileSerializer(user)  # Refresh serializer with updated data
                return Response({"message": "Profile updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = str(random.randint(100000, 999999))
            cache.set(f"forgot_otp_{email}", otp_code, timeout=300)  # 5 minutes expiry

            send_mail(
                subject="Your OTP for Password Reset",
                message=f"Your OTP is {otp_code}. It expires in 5 minutes.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"message": "OTP sent to your email. Please verify within 5 minutes."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyForgotPasswordOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyForgotPasswordOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp_code']
            new_password = serializer.validated_data['new_password']

            stored_otp = cache.get(f"forgot_otp_{email}")
            if not stored_otp:
                return Response({"error": "OTP expired or invalid request."}, status=status.HTTP_400_BAD_REQUEST)

            if stored_otp != otp_code:
                return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            cache.delete(f"forgot_otp_{email}")
            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)