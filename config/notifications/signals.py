from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from notifications.models import NotificationSettings

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_settings(sender, instance, created, **kwargs):
    """
    Signal handler to create NotificationSettings when a new User is created.

    Args:
        sender (class): The class from which the signal is sent (User).
        instance (User): The instance of the User model being saved.
        created (bool): Indicates whether a new instance was created.
        **kwargs: Additional keyword arguments.
    """
    if created:
        NotificationSettings.objects.create(user=instance)
