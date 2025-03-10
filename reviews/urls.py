from django.urls import path
from .views import (
    CreateReviewView, UserReviewsView, BadgeStatusView,
    ListUnreviewedRideMembersView  # Added new view
)

urlpatterns = [
    path('create/', CreateReviewView.as_view(), name='create_review'),
    path('user/<int:user_id>/', UserReviewsView.as_view(), name='user_reviews'),
    path('badge/<int:user_id>/', BadgeStatusView.as_view(), name='badge_status'),
    path('ride/<int:ride_id>/unreviewed/', ListUnreviewedRideMembersView.as_view(), name='list_unreviewed_members'),
]