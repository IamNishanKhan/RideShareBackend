from django.db import models
from users.models import User

class NotificationPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    origin_latitude = models.FloatField(null=True, blank=True)  # Store origin latitude
    origin_longitude = models.FloatField(null=True, blank=True)  # Store origin longitude
    destination_latitude = models.FloatField(null=True, blank=True)  # Store destination latitude
    destination_longitude = models.FloatField(null=True, blank=True)  # Store destination longitude
    vehicle_type = models.CharField(max_length=20, choices=[('bike', 'Bike'), ('cng', 'CNG'), ('car', 'Car')], null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Preference for {self.user.username}"

    @property
    def origin(self):
        """Return a tuple of (latitude, longitude) for the origin."""
        return (self.origin_latitude, self.origin_longitude) if self.origin_latitude and self.origin_longitude else None

    @property
    def destination(self):
        """Return a tuple of (latitude, longitude) for the destination."""
        return (self.destination_latitude, self.destination_longitude) if self.destination_latitude and self.destination_longitude else None
