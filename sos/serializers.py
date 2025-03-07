# sos/serializers.py
from rest_framework import serializers
from .models import SOSAlert
from users.models import User
import requests
from django.conf import settings

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']

class SOSAlertSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    notified_users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False  # Optional; if provided, use these; otherwise, calculate radius
    )
    location = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SOSAlert
        fields = ['id', 'user', 'latitude', 'longitude', 'timestamp', 'notified_users', 'status', 'escalated_from', 'location']
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
        sos_alert = SOSAlert.objects.create(user=user, **validated_data)

        if notified_users:
            # Use explicitly selected users
            sos_alert.notified_users.set(notified_users)
        elif sos_alert.latitude and sos_alert.longitude:
            # Calculate nearby users using Google Maps API
            nearby_users = self.get_nearby_users(sos_alert.latitude, sos_alert.longitude)
            sos_alert.notified_users.set(nearby_users.exclude(id=user.id))  # Exclude sender

        return sos_alert

    def get_nearby_users(self, latitude, longitude, radius_km=5):
        # Fetch all users with location data
        users = User.objects.filter(latitude__isnull=False, longitude__isnull=False)
        if not users.exists():
            return User.objects.none()

        # Prepare origins (SOS location) and destinations (user locations)
        origin = f"{latitude},{longitude}"
        destinations = '|'.join(f"{user.latitude},{user.longitude}" for user in users)

        # Call Google Maps Distance Matrix API
        url = (
            "https://maps.googleapis.com/maps/api/distancematrix/json?"
            f"origins={origin}&destinations={destinations}&units=metric&key={settings.GOOGLE_MAPS_API_KEY}"
        )
        response = requests.get(url)
        data = response.json()

        if data['status'] != 'OK':
            raise serializers.ValidationError("Error with Google Maps API: " + data.get('error_message', 'Unknown error'))

        # Filter users within radius
        nearby_users = []
        for i, row in enumerate(data['rows'][0]['elements']):
            if row['status'] == 'OK':
                distance_m = row['distance']['value']  # Distance in meters
                if distance_m <= radius_km * 1000:  # Convert km to meters
                    nearby_users.append(users[i])

        return User.objects.filter(id__in=[user.id for user in nearby_users])