# serializers.py
from rest_framework import serializers
from .models import Review, Badge
from users.models import User
from rides.models import Ride

class SimplifiedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']

class SimplifiedRideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = ['id', 'vehicle_type', 'pickup_name', 'destination_name', 'departure_time']

class ReviewSerializer(serializers.ModelSerializer):
    ride = SimplifiedRideSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'ride', 'rating', 'comment']
        read_only_fields = ['id']

class BadgeSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    total_rides = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ['level', 'average_rating', 'total_rides']
        read_only_fields = ['level', 'average_rating', 'total_rides']

    def get_average_rating(self, obj):
        return obj.get_average_rating()

    def get_total_rides(self, obj):
        # Count completed rides where user was either host or member
        return (Ride.objects.filter(host=obj.user, is_completed=True) | 
                Ride.objects.filter(members=obj.user, is_completed=True)).distinct().count()