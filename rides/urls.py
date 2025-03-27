from django.urls import path
from .views import (
    CreateRideView, JoinRideByIdView, JoinRideByCodeView, DeleteRideView,
    ListRidesView, LeaveRideView, CurrentRidesView, RideHistoryView, CompleteRideView,
    RideDetailView
)

urlpatterns = [
    path('create/', CreateRideView.as_view(), name='create_ride'),
    path('join/<int:ride_id>/', JoinRideByIdView.as_view(), name='join_ride_by_id'),
    path('join-by-code/', JoinRideByCodeView.as_view(), name='join_ride_by_code'),
    path('delete/<int:ride_id>/', DeleteRideView.as_view(), name='delete_ride'),
    path('list/', ListRidesView.as_view(), name='list_rides'),
    path('<int:ride_id>/', RideDetailView.as_view(), name='ride_detail'),
    path('leave/<int:ride_id>/', LeaveRideView.as_view(), name='leave_ride'),
    path('current/', CurrentRidesView.as_view(), name='current_rides'),
    path('history/', RideHistoryView.as_view(), name='ride_history'),
    path('<int:ride_id>/complete/', CompleteRideView.as_view(), name='complete_ride'),
]