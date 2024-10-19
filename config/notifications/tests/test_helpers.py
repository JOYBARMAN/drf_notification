from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from rest_framework_simplejwt.tokens import RefreshToken

from notifications.models import Notification
from notifications.utils import create_notification_json

from channels.db import database_sync_to_async


@database_sync_to_async
def create_user(**kwargs):
    """Create user for testing"""
    user_model = get_user_model()
    user = user_model.objects.create_user(kwargs)
    return user


@database_sync_to_async
def get_user_token(user):
    """Get user token for testing"""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
    }


def get_user_list():
    """Get all users"""
    user_model = get_user_model()
    return user_model.objects.all()


def create_notification(
    model_data: QuerySet, serializer, user_list, notification_message: list, requested_user
):
    """Create a notification for testing"""
    for notification in notification_message:
        notification_data = create_notification_json(
            message=notification["message"],
            method=notification["method"],
            instance=model_data,
            serializer=serializer,
        )

        # Create a notification
        notification = Notification().create_notification_for_users(
            notification_data=notification_data, users=user_list, requested_user=requested_user
        )

    return
