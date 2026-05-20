from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    default_budget = models.IntegerField(default=20000)
    default_travel_mode = models.CharField(max_length=20, choices=[('Car', 'Car'), ('Bus', 'Bus'), ('Train', 'Train')], default='Bus')
    interests_csv = models.CharField(max_length=500, blank=True, default='')
    food_preferences = models.CharField(max_length=500, blank=True, default='')
    accommodation_preferences = models.CharField(max_length=500, blank=True, default='')
    activity_preferences = models.CharField(max_length=500, blank=True, default='')
    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Destination(models.Model):
    CATEGORY_CHOICES = [
        ('Nature', 'Nature'),
        ('Culture', 'Culture'),
        ('Temple', 'Temple'),
        ('Beach', 'Beach'),
        ('Adventure', 'Adventure'),
        ('Food', 'Food'),
        ('History', 'History'),
        ('Wildlife', 'Wildlife'),
    ]

    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100, default='Sri Lanka')
    description = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Nature')
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', 'name']

    def __str__(self):
        return f"{self.name} ({self.country})"


class TripPlan(models.Model):
    TRAVEL_MODE_CHOICES = [
        ('Car', 'Car'),
        ('Bus', 'Bus'),
        ('Train', 'Train'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trip_plans')
    origin = models.CharField(max_length=200)
    destination_city = models.CharField(max_length=200)
    destination_country = models.CharField(max_length=100, default='Sri Lanka')
    start_date = models.DateField()
    end_date = models.DateField()
    interests = models.CharField(max_length=500)
    food_preferences = models.CharField(max_length=500, blank=True, default='')
    accommodation_preferences = models.CharField(max_length=500, blank=True, default='')
    activity_preferences = models.CharField(max_length=500, blank=True, default='')
    budget = models.IntegerField()
    travel_mode = models.CharField(max_length=20, choices=TRAVEL_MODE_CHOICES, default='Car')
    plan_json = models.JSONField()          # Full AI-generated plan
    weather_summary = models.CharField(max_length=500, blank=True)
    map_url = models.URLField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.origin} → {self.destination_city} ({self.start_date})"
