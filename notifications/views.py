from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import NotificationPreference
from .serializers import NotificationPreferenceSerializer
from rides.models import Ride
import requests
from django.conf import settings

class NotificationPreferenceView(APIView):
    def post(self, request):
        serializer = NotificationPreferenceSerializer(data={**request.data, 'user': request.user.id})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        preferences = NotificationPreference.objects.filter(user=request.user)
        serializer = NotificationPreferenceSerializer(preferences, many=True)
        return Response(serializer.data)

class NotifyMatchingRidesView(APIView):
    def post(self, request, ride_id):
        try:
            ride = Ride.objects.get(id=ride_id)
            preferences = NotificationPreference.objects.filter(
                origin__distance_lte=(ride.origin, D(km=5)),  # Example radius
                destination__distance_lte=(ride.destination, D(km=5)),
                vehicle_type=ride.vehicle_type,
                is_active=True
            ).exclude(user=ride.creator)
            for preference in preferences:
                self.send_push_notification(preference.user, ride)
            return Response({"message": "Notifications sent"}, status=status.HTTP_200_OK)
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND)

    def send_push_notification(self, user, ride):
        # Placeholder for Expo/FCM push notification implementation
        print(f"Sending ride notification to {user.username} for Ride {ride.id}")