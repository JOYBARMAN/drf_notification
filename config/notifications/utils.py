import logging
import jsonschema

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rest_framework_simplejwt.tokens import AccessToken

from notifications.choices import NotificationsStatus
from notifications.schema_validations import NOTIFICATION_SCHEMA
from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer

from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync


User = get_user_model()
logger = logging.getLogger(__name__)


def validate_token(token):
    """Validate the token and return the user_id"""
    try:
        access_token = AccessToken(token)
        user_id = access_token.payload["user_id"]
        return user_id
    except Exception as e:
        logger.error(f"{e}")
        return None


def get_group_name(user):
    """Create a group name for the user"""
    return f"user_{user.id}"


@database_sync_to_async
def get_user(user_id):
    """Get user from the database"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User not found")
        return None


def get_serialized_notifications(
    user,
):
    """Get notifications for the user and return serialized data"""
    try:
        notifications = Notification().get_current_user_notifications(user=user)
    except ValueError as e:
        return {"error": str(e)}

    serialized_data = UserNotificationListWithCountSerializer(notifications).data
    return serialized_data


def update_notification_read_status(notifications, is_read=True):
    """Update the read status of the notifications"""
    for notification in notifications:
        notification.is_read = is_read
        notification.save_dirty_fields()

    return notifications


def update_notification_status(notifications, status: NotificationsStatus):
    """Update the status of the notifications"""
    for notification in notifications:
        notification.status = status
        notification.save_dirty_fields()

    return notifications


def validate_notification(notification_data: dict, use_for_model=False):
    """
    Perform JSON schema validation for the notification field.
    """
    try:
        jsonschema.validate(instance=notification_data, schema=NOTIFICATION_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:

        valid_schema_message = {
            "message": "Your Message you want to send in notification",
            "object": {"Your Model Object"},
        }

        message = f"Notification object must be a valid JSON schema such as {valid_schema_message}"

        if use_for_model:
            raise ValidationError(message)

        raise ValueError(message)


def add_user_notification_to_group(user, channel_layer):
    """Add user notification to the group for broadcasting"""

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
