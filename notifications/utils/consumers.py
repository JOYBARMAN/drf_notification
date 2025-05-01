import logging

from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import AccessToken

from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync


# Get the user model
User = get_user_model()
# Get the logger
logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user(user_id):
    """Get user from the database"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


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


def add_user_notification_to_group(user, channel_layer):
    """Add user notification to the group for broadcasting"""
    # Send the data to the user's group
    group_name = get_group_name(user=user)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "notification.update",
        },
    )


def get_token_from_scope(scope):
    """Extract the token from the scope."""

    headers = dict(scope.get("headers", {}))

    # Extract the authorizations header
    authorization = headers.get(b"authorization")

    if authorization:
        # Decode the bytes to a string
        decoded_auth = authorization.decode("utf-8")
        # Split the string and check if it contains at least two parts
        parts = decoded_auth.split(" ")
        if len(parts) == 2 and parts[0] == "Bearer":
            return parts[1]
    else:
        return None
