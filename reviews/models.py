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
        unique_together = ('reviewer', 'reviewed_user', 'ride')  # One review per user per ride

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
        ('Good', 'Good'),        # 3 rides with avg 4+ stars
        ('Reliable', 'Reliable'), # 10 rides with avg 4+ stars
        ('Hero', 'Hero'),        # 25 rides with avg 4+ stars
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='badge')
    level = models.CharField(max_length=20, choices=BADGE_LEVELS, default='Good')
    updated_at = models.DateTimeField(auto_now=True)

    def update_badge(self):
        """Update badge based on average rating and number of reviews."""
        reviews = Review.objects.filter(reviewed_user=self.user)
        if reviews.exists():
            avg_rating = sum(review.rating for review in reviews) / reviews.count()
            high_rating_rides = reviews.filter(rating__gte=4).count()

            if high_rating_rides >= 25 and avg_rating >= 4:
                self.level = 'Hero'
            elif high_rating_rides >= 10 and avg_rating >= 4:
                self.level = 'Reliable'
            elif high_rating_rides >= 3 and avg_rating >= 4:
                self.level = 'Good'
            self.save()

    def get_average_rating(self):
        """Calculate the average rating for the user."""
        reviews = Review.objects.filter(reviewed_user=self.user)
        if reviews.exists():
            return sum(review.rating for review in reviews) / reviews.count()
        return 0

    def __str__(self):
        return f"{self.user} - {self.level}"