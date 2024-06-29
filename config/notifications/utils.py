import logging

from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import AccessToken

from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer

from channels.db import database_sync_to_async


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
    notifications = Notification().get_current_user_notifications(user=user)
    serialized_data = UserNotificationListWithCountSerializer(notifications).data
    return serialized_data
