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
        return False  # Prevent deleting messages via admin

# Register the Ride model with the inline
@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('ride_code', 'host', 'vehicle_type', 'pickup_name', 'destination_name', 'seats_available', 'is_completed', 'is_female_only')
    search_fields = ('ride_code', 'host__first_name', 'host__last_name', 'pickup_name', 'destination_name')
    list_filter = ('is_female_only','vehicle_type', 'is_completed', 'departure_time')
    inlines = [ChatMessageInline]
    ordering = ('-departure_time',)

    # Prevent deletion of rides with members (enforce via view)
    def has_delete_permission(self, request, obj=None):
        if obj and obj.members.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(RideRequest)
class RideRequestAdmin(admin.ModelAdmin):
    list_display = ('ride', 'user', 'requested_at', 'is_approved')
    list_filter = ('is_approved', 'requested_at')
    search_fields = ('ride__ride_code', 'user__first_name', 'user__last_name')