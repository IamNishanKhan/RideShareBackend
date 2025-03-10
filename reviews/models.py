from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from rides.models import Ride

class Review(models.Model):
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    reviewed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reviewer', 'reviewed_user', 'ride')

    def clean(self):
        if self.reviewer == self.reviewed_user:
            raise ValidationError("You cannot review yourself.")
        if not self.ride.is_completed:
            raise ValidationError("You cannot review yet because the ride is not completed.")
        if self.ride.host != self.reviewer and self.reviewer not in self.ride.members.all():
            raise ValidationError("You can only review members of a ride you participated in.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reviewer} reviewed {self.reviewed_user} for ride {self.ride}"

class Badge(models.Model):
    BADGE_LEVELS = [
        ('New', 'New'),            # < 3 completed rides
        ('Participant', 'Participant'),  # 3+ rides, avg < 4
        ('Good', 'Good'),          # 3+ rides, avg 4+ stars
        ('Reliable', 'Reliable'),  # 10+ rides, avg 4+ stars
        ('Hero', 'Hero'),          # 25+ rides, avg 4+ stars
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='badge')
    level = models.CharField(max_length=20, choices=BADGE_LEVELS, default='New')
    updated_at = models.DateTimeField(auto_now=True)

    def update_badge(self):
        """Update badge based on average rating and number of completed rides with reviews."""
        # Get all reviews for this user
        reviews = Review.objects.filter(reviewed_user=self.user)
        review_count = reviews.count()

        # Count completed rides where the user was either host or member
        completed_rides = (Ride.objects.filter(host=self.user, is_completed=True) | 
                          Ride.objects.filter(members=self.user, is_completed=True)).distinct().count()

        # Calculate average rating
        if review_count > 0:
            avg_rating = sum(review.rating for review in reviews) / review_count
        else:
            avg_rating = 0

        # Badge logic based on completed rides and average rating
        if completed_rides >= 25 and avg_rating >= 4:
            self.level = 'Hero'
        elif completed_rides >= 10 and avg_rating >= 4:
            self.level = 'Reliable'
        elif completed_rides >= 3 and avg_rating >= 4:
            self.level = 'Good'
        elif completed_rides >= 3:  # 3+ rides but avg < 4
            self.level = 'Participant'
        else:
            self.level = 'New'  # < 3 rides
        
        self.save()

    def get_average_rating(self):
        """Calculate the average rating for the user."""
        reviews = Review.objects.filter(reviewed_user=self.user)
        if reviews.exists():
            return sum(review.rating for review in reviews) / reviews.count()
        return 0

    def __str__(self):
        return f"{self.user} - {self.level}"