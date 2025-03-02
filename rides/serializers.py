from rest_framework import serializers
from .models import Ride, RideRequest
from users.serializers import UserProfileSerializer

class RideSerializer(serializers.ModelSerializer):
    host = UserProfileSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    per_person_fare = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'host', 'vehicle_type', 'pickup_name', 'pickup_longitude', 'pickup_latitude',
            'destination_name', 'destination_longitude', 'destination_latitude', 'departure_time',
            'total_fare', 'per_person_fare', 'seats_available', 'is_female_only', 'vehicle_number_plate',
            'ride_code', 'is_completed', 'created_at', 'members'
        ]
        read_only_fields = ['id', 'host', 'created_at', 'ride_code', 'is_completed', 'seats_available']

    def get_per_person_fare(self, obj):
        total_members = obj.members.count() + 1  # Host + joined members
        return float(obj.total_fare / total_members) if total_members > 0 else float(obj.total_fare)

    def get_members(self, obj):
        members = list(obj.members.all())
        members.insert(0, obj.host)
        return UserProfileSerializer(members, many=True).data

    def validate(self, data):
        required_fields = ['vehicle_type', 'pickup_name', 'destination_name', 'departure_time', 'total_fare', 'is_female_only']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise serializers.ValidationError(f"{field} is required.")
        return data

class RideRequestSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    ride = RideSerializer(read_only=True)

    class Meta:
        model = RideRequest
        fields = ['id', 'ride', 'user', 'requested_at', 'is_approved']
        read_only_fields = ['id', 'user', 'requested_at', 'is_approved']