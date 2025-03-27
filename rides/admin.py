from django.contrib import admin
from .models import Ride, RideRequest
from chat.models import ChatMessage

# Define an inline for ChatMessage
class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0  # No extra empty forms by default
    readonly_fields = ('message_json', 'timestamp')  # Make these fields read-only
    fields = ('message_json', 'timestamp', 'user')  # Fields to display in the inline

    def has_add_permission(self, request, obj):
        return False  # Prevent adding new messages via admin

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Allow deletion only for superusers

# Register the Ride model with the inline
@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('pk', 'ride_code', 'host', 'vehicle_type', 'pickup_name', 'destination_name', 'seats_available', 'is_completed')
    search_fields = ('ride_code', 'host__first_name', 'host__last_name', 'pickup_name', 'destination_name')
    list_filter = ('vehicle_type', 'is_completed', 'departure_time')
    inlines = [ChatMessageInline]
    ordering = ('-departure_time',)

    # Allow deletion of rides, which will cascade to chat messages
    def has_delete_permission(self, request, obj=None):
        if obj and obj.members.exists():
            return False  # Prevent deletion if there are members
        return request.user.is_superuser  # Only superusers can delete

@admin.register(RideRequest)
class RideRequestAdmin(admin.ModelAdmin):
    list_display = ('ride', 'user', 'requested_at', 'is_approved')
    list_filter = ('is_approved', 'requested_at')
    search_fields = ('ride__ride_code', 'user__first_name', 'user__last_name')