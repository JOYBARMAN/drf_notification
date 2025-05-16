import threading

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache

from notifications.models import NotificationSettings, Notification
from notifications.utils.consumers import (
    add_user_notification_to_group,
)
from notifications.managers import bulk_post_save

from channels.layers import get_channel_layer


# Get the channel layer
channel_layer = get_channel_layer()
# Get the user model
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
    bulk_post_save.send(
        sender=Notification, instances=[instance], created=kwargs.get("created", False)
    )


@receiver(bulk_post_save)
def handle_bulk_post_save(sender, instances, created, **kwargs):
    def background_task():
        for instance in instances:
            if instance.user:
                user = instance.user
                # Remove cache for the user
                cache.delete(user.id)
                # Add user notification to group
                add_user_notification_to_group(user=user, channel_layer=channel_layer)

    threading.Thread(target=background_task).start()
