# sos/models.py
from django.db import models
from users.models import User

class SOSAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notified_users = models.ManyToManyField(User, related_name='sos_notifications', blank=True)
    status = models.CharField(max_length=20, default='active')
    escalated_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)  # Tracks SOS chain

    def __str__(self):
        lat = f"{self.latitude:.4f}" if self.latitude is not None else "None"
        lon = f"{self.longitude:.4f}" if self.longitude is not None else "None"
        return f"SOS by {self.user.username} at ({lat}, {lon})"

    @property
    def location(self):
        return (self.latitude, self.longitude) if self.latitude and self.longitude else None