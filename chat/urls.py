from django.urls import path
from . import views

urlpatterns = [
    path('ride/<int:ride_id>/', views.chat_room, name='chat_room'),
]