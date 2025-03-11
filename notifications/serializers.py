from rest_framework import serializers
from .models import NotificationPreference
from users.serializers import UserRegistrationSerializer

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    user = UserRegistrationSerializer(read_only=True)

    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'origin', 'destination', 'vehicle_type', 'is_active']
