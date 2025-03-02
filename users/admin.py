from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'student_id', 'gender', 'is_active')
    list_filter = ('gender', 'is_active')
    search_fields = ('email', 'student_id', 'first_name', 'last_name')