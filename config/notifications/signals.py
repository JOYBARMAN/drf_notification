from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
from django.contrib.auth import get_user_model

from notifications.models import NotificationSettings, Notification
from notifications.utils import (
    add_user_notification_to_group,
    # add_multiple_user_notifications_to_group,
)

from channels.layers import get_channel_layer

# Define the custom signal
post_bulk_create = Signal()

# Get the channel layer
channel_layer = get_channel_layer()

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_settings(sender, instance, created, **kwargs):
    """Handles the post_save signal for User instances."""
    if created:
        NotificationSettings.objects.create(user=instance)


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def notification_change(sender, instance, **kwargs):
    """Handles the post_save and post_delete signals for Notification instances."""
    if instance.user:
        user = instance.user

        # Add user notification to group
        add_user_notification_to_group(user=user, channel_layer=channel_layer)


# @receiver(post_bulk_create, sender=Notification)
# def handle_post_bulk_create(sender, instances, **kwargs):
#     """Handles the post_bulk_create signal for Notification instances."""

#     users = [instance.user for instance in instances]
#     add_multiple_user_notifications_to_group(users=users, channel_layer=channel_layer)
