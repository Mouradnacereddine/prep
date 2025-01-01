from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Signal to handle user creation events."""
    if created:
        # Add any additional setup needed when a user is created
        pass
