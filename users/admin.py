from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class UserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password1', 'password2')

class UserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password', 'is_active', 'is_staff')

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    list_display = ('id', 'email', 'first_name', 'last_name', 'student_id', 'gender', 'is_active')
    list_filter = ('gender', 'is_active')
    search_fields = ('email', 'student_id', 'first_name', 'last_name')
    ordering = ['email']  # Override the default ordering to use 'email' instead of 'username'
    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser',),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:  # This is the add user page
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing user
            return self.readonly_fields
        return []