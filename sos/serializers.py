# sos/serializers.py
from rest_framework import serializers
from .models import SOSAlert, EmergencyContact
from users.models import User
import requests
from django.conf import settings

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'sound_enabled', 'location_enabled', 'notifications_enabled',
            'vibration_enabled', 'emergency_message'
        ]

class EmergencyContactSerializer(serializers.ModelSerializer):
    contact = UserSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='contact', write_only=True
    )

    class Meta:
        model = EmergencyContact
        fields = ['id', 'contact', 'contact_id', 'added_at']
        read_only_fields = ['added_at']

class SOSAlertSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    notified_users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False
    )
    location = serializers.SerializerMethodField(read_only=True)
    is_community_alert = serializers.BooleanField(default=False, required=False)

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
            sos_alert.notified_users.set(notified_users)
        elif is_community_alert:
            nearby_users = self.get_nearby_users(sos_alert.latitude, sos_alert.longitude)
            sos_alert.notified_users.set(nearby_users.exclude(id=user.id))
        else:
            nearby_users = self.get_nearby_users(sos_alert.latitude, sos_alert.longitude)
            sos_alert.notified_users.set(nearby_users.exclude(id=user.id))

        custom_message = user.emergency_message or "An SOS alert has been created near you."
        self.send_expo_notifications(sos_alert, custom_message)
        return sos_alert

    def get_nearby_users(self, latitude, longitude, radius_km=5):
        users = User.objects.filter(latitude__isnull=False, longitude__isnull=False)
        if not users.exists():
            return User.objects.none()

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
                distance_m = row['distance']['value']
                if distance_m <= radius_km * 1000:
                    nearby_users.append(users[i])

        return User.objects.filter(id__in=[user.id for user in nearby_users])

    def send_expo_notifications(self, sos_alert, custom_message=None):
        notified = sos_alert.notified_users.all()
        if not notified:
            return

        messages = []
        for user in notified:
            if user.expo_push_token:
                message_body = custom_message.format(location=sos_alert.location) if custom_message else f"An SOS alert has been created near you at {sos_alert.location}."
                messages.append({
                    "to": user.expo_push_token,
                    "sound": "default",
                    "title": "SOS Alert",
                    "body": message_body,
                    "data": {"sos_alert_id": sos_alert.id}
                })

        if not messages:
            return

        url = "https://exp.host/--/api/v2/push/send"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=messages, headers=headers)

        if response.status_code != 200:
            print(f"Failed to send Expo notifications: {response.text}")
        else:
            print(f"Expo notifications sent successfully to {len(messages)} users")