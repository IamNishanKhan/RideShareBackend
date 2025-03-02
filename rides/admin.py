from django.contrib import admin
from .models import Ride, RideRequest

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('id', 'ride_code', 'host', 'vehicle_type', 'pickup_name', 'destination_name', 'departure_time', 'seats_available', 'is_female_only', 'is_completed')
    list_filter = ('vehicle_type', 'is_female_only', 'is_completed')
    search_fields = ('ride_code', 'pickup_name', 'destination_name')

@admin.register(RideRequest)
class RideRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'ride', 'user', 'requested_at', 'is_approved')
    list_filter = ('is_approved',)