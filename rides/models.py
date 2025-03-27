from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
import random
import string

def generate_ride_code():
    """Generate a unique 6-character alphanumeric code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

class Ride(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('Private Car', 'Private Car'),
        ('Private Bike', 'Private Bike'),
        ('CNG', 'CNG'),
        ('Uber', 'Uber'),
        ('Taxi', 'Taxi'),
        ('Rickshaw', 'Rickshaw'),
    ]

    id = models.AutoField(primary_key=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rides')
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    pickup_name = models.CharField(max_length=100)
    destination_name = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    seats_available = models.PositiveIntegerField(editable=False)
    is_female_only = models.BooleanField(default=False)
    ride_code = models.CharField(max_length=6, unique=True, default=generate_ride_code)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name='ride_members', blank=True)
    pickup_longitude = models.FloatField(null=True, blank=True)
    pickup_latitude = models.FloatField(null=True, blank=True)
    destination_longitude = models.FloatField(null=True, blank=True)
    destination_latitude = models.FloatField(null=True, blank=True)
    vehicle_number_plate = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        ordering = ['-departure_time']

    def get_max_seats(self):
        """Return maximum seats based on vehicle_type."""
        max_seats = {
            'CNG': 3,
            'Uber': 3,
            'Taxi': 3,
            'Private Car': 3,
            'Private Bike': 2,
            'Rickshaw': 2,
        }
        return max_seats.get(self.vehicle_type, 3)

    def set_initial_seats(self):
        """Set initial seats_available (max seats - 1 for host)."""
        return self.get_max_seats() - 1

    def clean(self):
        if self.is_female_only and self.host.gender != 'Female':
            raise ValidationError("Only female hosts can create female-only ride groups.")

    def save(self, *args, **kwargs):
        # Check if this is an update and is_completed has changed to True
        if self.pk:  # If the instance already exists (update)
            old_instance = Ride.objects.get(pk=self.pk)
            if not old_instance.is_completed and self.is_completed:
                # Ride just completed, delete all chat messages immediately
                self.chat_messages.all().delete()

        # Set seats_available only on creation
        if not self.pk:
            self.seats_available = self.set_initial_seats()

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete all associated chat messages before deleting the ride
        self.chat_messages.all().delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle_type} ({self.ride_code}) from {self.pickup_name} to {self.destination_name}"

class RideRequest(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('ride', 'user')

    def clean(self):
        if self.ride.is_female_only and self.user.gender != 'Female':
            raise ValidationError("Only female users can join female-only ride groups.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} requested to join {self.ride}"