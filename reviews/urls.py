from django.urls import path
from .views import CreateReviewView, UserReviewsView

urlpatterns = [
    path('create/', CreateReviewView.as_view(), name='create_review'),
    path('user/<int:user_id>/', UserReviewsView.as_view(), name='user_reviews'),
]