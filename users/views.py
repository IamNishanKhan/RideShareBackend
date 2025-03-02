from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserRegistrationSerializer, UserProfileSerializer, UserLoginSerializer
from .models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import random

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if User.objects.filter(email=email).exists():
                return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a 6-digit OTP
            otp_code = str(random.randint(100000, 999999))

            # Store user data and OTP in cache with 5-minute timeout (300 seconds)
            cache.set(f"pending_user_{email}", serializer.validated_data, timeout=300)
            cache.set(f"otp_{email}", otp_code, timeout=300)

            # Send OTP email
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

        if not email or not otp_code:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        stored_otp = cache.get(f"otp_{email}")
        user_data = cache.get(f"pending_user_{email}")

        if not stored_otp or not user_data:
            return Response({"error": "OTP expired or invalid request."}, status=status.HTTP_400_BAD_REQUEST)

        if stored_otp != otp_code:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the user after OTP verification
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
            user.save()

        # Generate tokens and return user data
        refresh = RefreshToken.for_user(user)
        user_data_serialized = UserProfileSerializer(user).data
        response_data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user_data_serialized
        }

        # Clear cache after successful registration
        cache.delete(f"otp_{email}")
        cache.delete(f"pending_user_{email}")

        return Response(response_data, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
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

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            if 'profile_photo' in request.FILES:
                request.user.profile_photo = request.FILES['profile_photo']
                request.user.save()
            serializer.save()
            return Response({"message": "Profile updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)