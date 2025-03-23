# sos/admin.py
from django.contrib import admin
from .models import SOSAlert, EmergencyContact

@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'location_display', 'status', 'is_community_alert', 'notified_users_count')
    list_filter = ('status', 'is_community_alert', 'timestamp')
    search_fields = ('user__username', 'user__email', 'status')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'location_display')
    raw_id_fields = ('user', 'notified_users', 'escalated_from')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'is_community_alert')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'location_display')
        }),
        ('Relationships', {
            'fields': ('notified_users', 'escalated_from')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )

    def location_display(self, obj):
        lat = f"{obj.latitude:.4f}" if obj.latitude is not None else "N/A"
        lon = f"{obj.longitude:.4f}" if obj.longitude is not None else "N/A"
        return f"({lat}, {lon})"
    location_display.short_description = 'Location'

    def notified_users_count(self, obj):
        return obj.notified_users.count()
    notified_users_count.short_description = 'Notified Users'

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'contact', 'added_at', 'user_email', 'contact_email')
    list_filter = ('added_at', 'user', 'contact')
    search_fields = ('user__username', 'contact__username', 'user__email', 'contact__email')
    date_hierarchy = 'added_at'
    readonly_fields = ('added_at', 'user_email', 'contact_email')
    raw_id_fields = ('user', 'contact')
    list_select_related = ('user', 'contact')

    fieldsets = (
        (None, {
            'fields': ('user', 'contact')
        }),
        ('Details', {
            'fields': ('user_email', 'contact_email')
        }),
        ('Timestamp', {
            'fields': ('added_at',)
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def contact_email(self, obj):
        return obj.contact.email
    contact_email.short_description = 'Contact Email'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'contact')