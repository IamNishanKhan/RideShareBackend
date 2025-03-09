from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ride/(?P<ride_id>\d+)/$', consumers.RideChatConsumer.as_asgi()),
]