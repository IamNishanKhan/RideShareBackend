from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('ride', 'user', 'message_preview', 'timestamp')
    search_fields = ('ride__ride_code', 'user__first_name', 'user__last_name')
    list_filter = ('ride', 'timestamp')
    readonly_fields = ('message_json',)

    def message_preview(self, obj):
        return obj.message_json.get('message', 'No message')[:50] if obj.message_json else 'No data'
    message_preview.short_description = 'Message Preview'

    # Allow deletion of ChatMessage objects
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete