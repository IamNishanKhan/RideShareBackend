from rest_framework import serializers
from .models import SOSAlert
from users.models import User
import requests
from django.conf import settings

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']

class SOSAlertSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    notified_users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False
    )
    location = serializers.SerializerMethodField(read_only=True)
    is_community_alert = serializers.BooleanField(default=False, required=False)  # New field

    class Meta:
        model = SOSAlert
        fields = ['id', 'user', 'latitude', 'longitude', 'timestamp', 'notified_users', 'status', 'escalated_from', 'location', 'is_community_alert']
        read_only_fields = ['timestamp', 'status', 'location']

    def get_location(self, obj):
        return obj.location

    def validate(self, data):
        if not (data.get('latitude') and data.get('longitude')):
            raise serializers.ValidationError("Latitude and longitude are required.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        notified_users = validated_data.pop('notified_users', None)
        is_community_alert = validated_data.pop('is_community_alert', False)
        sos_alert = SOSAlert.objects.create(user=user, is_community_alert=is_community_alert, **validated_data)

        if notified_users:
            # Explicitly selected users
            sos_alert.notified_users.set(notified_users)
        elif is_community_alert:
            # Notify all users near the location based on their home location
            nearby_users = self.get_nearby_users(sos_alert.latitude, sos_alert.longitude)
            sos_alert.notified_users.set(nearby_users.exclude(id=user.id))
        else:
            # Default behavior: notify nearby users (e.g., within 5km)
            nearby_users = self.get_nearby_users(sos_alert.latitude, sos_alert.longitude)
            sos_alert.notified_users.set(nearby_users.exclude(id=user.id))

        # Simulate sending notifications (dummy response for now)
        self.send_dummy_notifications(sos_alert)
        return sos_alert

    def get_nearby_users(self, latitude, longitude, radius_km=5):
        users = User.objects.filter(latitude__isnull=False, longitude__isnull=False)
        if not users.exists():
            return User.objects.none()

        # Use Google Maps API for accurate distance calculation
        origin = f"{latitude},{longitude}"
        destinations = '|'.join(f"{user.latitude},{user.longitude}" for user in users)
        url = (
            f"https://maps.googleapis.com/maps/api/distancematrix/json?"
            f"origins={origin}&destinations={destinations}&units=metric&key={settings.GOOGLE_MAPS_API_KEY}"
        )
        response = requests.get(url)
        data = response.json()

        if data['status'] != 'OK':
            raise serializers.ValidationError("Error with Google Maps API: " + data.get('error_message', 'Unknown error'))

        nearby_users = []
        for i, row in enumerate(data['rows'][0]['elements']):
            if row['status'] == 'OK':
                distance_m = row['distance']['value']  # Distance in meters
                if distance_m <= radius_km * 1000:
                    nearby_users.append(users[i])

        return User.objects.filter(id__in=[user.id for user in nearby_users])

    def send_dummy_notifications(self, sos_alert):
        # Simulate sending notifications to notified_users
        notified = sos_alert.notified_users.all()
        for user in notified:
            # In a real app, you'd integrate SMS (e.g., Twilio) or push notifications here
            print(f"Dummy notification sent to {user.first_name} {user.last_name} ({user.phone_number})")