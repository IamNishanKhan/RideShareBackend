
from django.urls import path
from .views import NotificationPreferenceView, NotifyMatchingRidesView

urlpatterns = [
    path('preferences/', NotificationPreferenceView.as_view(), name='notification_preferences'),
    path('rides/<uuid:ride_id>/notify/', NotifyMatchingRidesView.as_view(), name='notify_matching_rides'),
]
