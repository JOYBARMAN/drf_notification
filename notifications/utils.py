import logging, json, jsonschema, threading

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import serializers
from django.db.models.query import QuerySet
from django.core.cache import cache
from django.forms.models import model_to_dict

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import ValidationError

from notifications.choices import NotificationsStatus
from notifications.schema_validations import NOTIFICATION_SCHEMA
from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer

from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync

# Get the user model
User = get_user_model()
# Get the logger
logger = logging.getLogger(__name__)
# Create a thread local object to store the user
_thread_locals = threading.local()
# Get the settings
ALLOWED_NOTIFICATION_DATA = getattr(settings, "ALLOWED_NOTIFICATION_DATA", False)
# Get the cache timeout
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


def get_user_serialized_notifications(user):
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
        notification.save()

    return notifications


def update_notification_status(notifications, status: NotificationsStatus):
    """Update the status of the notifications"""
    for notification in notifications:
        notification.status = status
        notification.save()

    return notifications


def validate_notification(notification_data: dict, use_for_model=False):
    """
    Perform JSON schema validation for the notification field.
    """
    from django.core.exceptions import ValidationError

    try:
        jsonschema.validate(instance=notification_data, schema=NOTIFICATION_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        # Create a readable message for notification message
        valid_schema_message = {
            "message": "Your Message you want to send in notification",
            "instance": {"Model instance, which model is responsible for notification"},
        }
        message = f"Notification object must be a valid JSON schema such as {valid_schema_message}"

        # If the validation is for model then raise ValidationError
        if use_for_model:
            raise ValidationError(message)

        raise ValueError(message)


def get_changed_fields(model_instance):
    """Get the changed fields of a model instance"""

    changed_data = {}

    # Fetch the current instance from the database
    original_instance = model_instance.__class__.objects.filter(
        pk=model_instance.pk
    ).first()

    if not original_instance:
        raise ValueError(
            "Provided model instance to get changed fields is not found in the database"
        )

    # Compare each field between the instance and its original state
    for field in model_instance._meta.fields:
        # Extract the field name and field type
        field_name = field.name
        field_type = field.__class__.__name__

        # Get the field value from the original and current instance
        original_value = getattr(original_instance, field_name)
        current_value = getattr(model_instance, field_name)

        # Handle model FK and O2O relationship changes
        if field_type in ["ForeignKey", "OneToOneField"]:
            original_value = model_to_dict(original_value) if original_value else None
            current_value = model_to_dict(current_value) if current_value else None

        # Handle JSONField comparison
        if field_type == "JSONField":
            changed_json_fields = compare_json_fields(
                original_value or {}, current_value or {}
            )
            if changed_json_fields:
                changed_data[field_name] = changed_json_fields
            continue

        if original_value != current_value:
            changed_data[field_name] = {
                "original": original_value,
                "new": current_value,
            }

    # Handle M2M relationship changes
    if model_instance._meta.many_to_many:
        changed_data = handle_many_to_many_field_comparison(
            changed_data, model_instance, original_instance
        )

    return changed_data


def handle_many_to_many_field_comparison(
    changed_data, model_instance, original_instance
):
    """Handle the many to many field comparison"""
    for m2m_field in model_instance._meta.many_to_many:
        field_name = m2m_field.name

        original_value = list(getattr(original_instance, field_name).all().values())
        current_value = list(getattr(model_instance, field_name).all().values())

        # Check if both original and current values are empty
        if not original_value and not current_value:
            continue

        # Use sets for comparison
        original_value_set = {tuple(item.items()) for item in original_value}
        current_value_set = {tuple(item.items()) for item in current_value}

        # Find the added and removed values
        added = current_value_set - original_value_set
        removed = original_value_set - current_value_set

        # Compare the M2M values
        if added or removed:
            changed_data[field_name] = {
                "original": original_value,
                "new": current_value,
                "added": list(added) if added else None,
                "removed": list(removed) if removed else None,
            }

    return changed_data


def compare_json_fields(original, current):
    """Compare two JSON objects and return only the changed fields."""
    changes = {}
    for key in set(original.keys()).union(current.keys()):
        if original.get(key) != current.get(key):
            changes[key] = {"original": original.get(key), "new": current.get(key)}
    return changes if changes else None


def create_notification_json(
    message: str = None,
    instance: QuerySet = None,
    serializer=None,
    method="UNDEFINED",
    changed_data: dict = {},
):
    """Create a notification field json data for notification model"""

    # Handle the required fields error
    required_fields = {"message": message, "instance": instance}
    for field_name, field_value in required_fields.items():
        if not field_value:
            raise ValidationError(f"{field_name} is required for notification")

    # Serialize the queryset/model to JSON
    if serializer:
        serialized_model = serializer(instance).data
    else:
        serialized_model = json.loads(serializers.serialize("json", [instance]))[0]

    # Arrange the notification object
    notification = {
        "message": message,
        "model": instance.__class__.__name__,
        "instance": serialized_model,
        "method": method,
        "changed_data": changed_data,
    }

    # Validate the notification against the schema
    validate_notification(notification)

    return notification


def add_user_notification_to_group(user, channel_layer):
    """Add user notification to the group for broadcasting"""

    # Fetch the user's serialized notifications
    notifications = get_user_serialized_notifications(user=user)

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


def get_current_user():
    """Get the current user from the thread local"""
    return getattr(_thread_locals, "user", None)


def set_current_user(user):
    """Set the current user in the thread local"""
    _thread_locals.user = user
