# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User
from sos.models import EmergencyContact

# Custom forms remain unchanged
class UserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password1', 'password2')

class UserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password', 'is_active', 'is_staff')

# Inline for Emergency Contacts with fk_name specified
class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1
    fk_name = 'user'  # Specify which ForeignKey to use (the user who owns the emergency contacts)
    raw_id_fields = ('contact',)
    readonly_fields = ('added_at',)
    verbose_name = "Emergency Contact"
    verbose_name_plural = "Emergency Contacts"

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    inlines = (EmergencyContactInline,)
    
    list_display = ('id', 'email', 'first_name', 'last_name', 'student_id', 'gender', 'is_active', 'emergency_contacts_count')
    list_filter = ('gender', 'is_active')
    search_fields = ('email', 'student_id', 'first_name', 'last_name')
    ordering = ['email']
    
    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',)}),
        ('Emergency Contacts', {'fields': ()}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'profile_photo', 'gender', 'student_id', 'expo_push_token', 'latitude', 'longitude', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser',),
        }),
    )

    def emergency_contacts_count(self, obj):
        return obj.emergency_contacts.count()
    emergency_contacts_count.short_description = 'Emergency Contacts'

    def get_fieldsets(self, request, obj=None):
        if not obj:  # This is the add user page
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing user
            return self.readonly_fields
        return []