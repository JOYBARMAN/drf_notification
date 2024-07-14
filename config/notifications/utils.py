import logging
import jsonschema
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import serializers
from django.db.models.query import QuerySet
from django.core.cache import cache

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import ValidationError

from notifications.choices import NotificationsStatus
from notifications.schema_validations import NOTIFICATION_SCHEMA
from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer

from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync


User = get_user_model()
logger = logging.getLogger(__name__)
ALLOWED_NOTIFICATION_DATA = getattr(settings, "ALLOWED_NOTIFICATION_DATA", False)
CACHE_TIMEOUT = getattr(settings, "CACHE_TIMEOUT", 60 * 60)


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
        return None


def serialized_notifications(notifications):
    """Serialize the notifications"""
    return UserNotificationListWithCountSerializer(notifications).data


def get_serialized_notifications(user):
    """Get notifications for the user and return serialized data"""
    try:
        notifications = Notification().get_current_user_notifications(user=user)
    except ValueError as e:
        return {"error": str(e)}

    serialized_notification = serialized_notifications(notifications)

    # Check is the user want to get the notification data in websocket response
    # If ALLOWED_NOTIFICATION_DATA=True in settings.py we show the notification data in websocket response
    if not ALLOWED_NOTIFICATION_DATA:
        serialized_notification.pop("notifications")
        return serialized_notification

    return serialized_notification


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
        # Create a readable message for notification message
        valid_schema_message = {
            "message": "Your Message you want to send in notification",
            "object": {"Model instance, which model is responsible for notification"},
        }
        message = f"Notification object must be a valid JSON schema such as {valid_schema_message}"

        # If the validation is for model then raise ValidationError
        if use_for_model:
            raise ValidationError(message)

        raise ValueError(message)


def create_notification_json(
    message: str = None, model: QuerySet = None, serializer=None, method="UNDEFINED"
):
    """Create a notification field json data for notification model"""

    # Handle the required fields error
    required_fields = {"message": message, "model": model}
    for field_name, field_value in required_fields.items():
        if not field_value:
            raise ValidationError(f"{field_name} is required for notification")

    # Serialize the queryset/model to JSON
    if serializer:
        serialized_model = serializer(model).data
    else:
        serialized_model = json.loads(serializers.serialize("json", [model]))[0]

    # Arrange the notification object
    notification = {
        "message": message,
        "object": serialized_model,
        "method": method,
    }

    # Validate the notification against the schema
    validate_notification(notification)

    return notification


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


def get_token_from_scope(scope):
    """Extract the token from the scope."""

    headers = dict(scope.get("headers", {}))

    # Extract the authorizations header
    authorizations = headers.get(b"authorizations")

    if authorizations:
        # Decode the bytes to a string
        decoded_auth = authorizations.decode("utf-8")
        # Split the string and check if it contains at least two parts
        parts = decoded_auth.split(" ")
        if len(parts) == 2 and parts[0] == "Bearer":
            return parts[1]
    else:
        return None


def generate_sub_key(query_params, page_number):
    """Generate a sub-key based on the query parameters and page number"""
    return f"{query_params}_{page_number}"


def get_user_cache_notifications(user, query_params, page_number):
    """Get the user's notifications from the cache"""
    cache_key = user.id

    # Fetch the cached data for the user
    user_cache = cache.get(cache_key, {})

    sub_key = generate_sub_key(query_params, page_number)

    # Try to get the cached data from the user's cache
    if sub_key in user_cache:
        return user_cache[sub_key]

    return None


def set_user_notifications_in_cache(user, query_params, page_number, queryset):
    """Cache the user's notifications"""
    user_cache = cache.get(user.id, {})

    sub_key = generate_sub_key(query_params, page_number)

    # Cache the queryset
    user_cache[sub_key] = queryset
    cache.set(user.id, user_cache, CACHE_TIMEOUT)

    return
