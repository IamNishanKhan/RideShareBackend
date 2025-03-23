# sos/urls.py
from django.urls import path
from .views import CreateSOSAlertView, ActiveSOSAlertsView, UserListView, EmergencyContactView, UserSettingsView

urlpatterns = [
    path('create/', CreateSOSAlertView.as_view(), name='create-sos'),
    path('active/', ActiveSOSAlertsView.as_view(), name='active-sos'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('emergency-contacts/', EmergencyContactView.as_view(), name='emergency-contacts'),
    path('settings/', UserSettingsView.as_view(), name='user-settings'),
]