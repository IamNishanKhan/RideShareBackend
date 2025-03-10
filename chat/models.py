from django.db import models
from users.models import User
from rides.models import Ride
import json

class ChatMessage(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message_json = models.JSONField(null=True, blank=True)  # Temporarily nullable
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} in Ride {self.ride.id}: {self.message_json.get('message', '')[:20]}"