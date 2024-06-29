from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from notifications.models import NotificationSettings, Notification
from notifications.utils import get_group_name, get_serialized_notifications

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


User = get_user_model()
channel_layer = get_channel_layer()


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


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def notification_change(sender, instance, **kwargs):
    """
    Reacts to changes in Notification objects.

    This function handles post-save and post-delete signals for Notification instances.
    Upon receiving these signals, it retrieves serialized notifications associated
    with the affected user and broadcasts the updated data to the appropriate user group.

    Args:
        sender: The model class sending the signal (Notification).
        instance: The specific instance of Notification that triggered the signal.
        **kwargs: Additional keyword arguments provided by the signal.

    Notes:
        - Requires a valid instance.user for processing.
        - Uses synchronous channel layer operations for group message broadcasting.

    Returns:
        None
    """
    if instance.user:
        user = instance.user

        # Fetch the user's serialized notifications
        notifications = get_serialized_notifications(user=user)

        # Send the data to the user's group
        group_name = get_group_name(user=user)
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification.update",
                "user_notifications": notifications,
            },
        )
