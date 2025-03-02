from django.contrib import admin
from .models import Review, Badge

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'reviewer', 'reviewed_user', 'ride', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('reviewer__email', 'reviewed_user__email', 'ride__ride_code')

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'updated_at')
    list_filter = ('level',)
    search_fields = ('user__email',)