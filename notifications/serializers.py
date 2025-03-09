from rest_framework import serializers
from .models import NotificationPreference
from users.serializers import NSUUserSerializer

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    user = NSUUserSerializer(read_only=True)

    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'origin', 'destination', 'vehicle_type', 'is_active']