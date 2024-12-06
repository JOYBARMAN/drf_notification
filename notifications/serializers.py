"""Serializer for notification related """

from django.conf import settings
from django.utils.module_loading import import_string
from django.contrib.auth import get_user_model

from rest_framework import serializers

from notifications.models import Notification
from notifications.choices import NotificationsStatus, NotificationsActionChoices

User = get_user_model()

def get_user_serializer():
    # Get the serializer path from settings, fallback to PrimaryKeyRelatedField
    user_serializer_class = import_string(getattr(settings, 'NOTIFICATION_USER_SERIALIZER', 'rest_framework.serializers.PrimaryKeyRelatedField'))

    # Check if it's a proper serializer class (i.e., has Meta), else fallback to PrimaryKeyRelatedField
    if not hasattr(user_serializer_class, 'Meta'):
        user_serializer_class = serializers.PrimaryKeyRelatedField

    return user_serializer_class


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for user"""

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
        ]

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification"""

    user = get_user_serializer()(read_only=True)
    created_by = get_user_serializer()(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "uid",
            "user",
            "notification",
            "is_read",
            "custom_info",
            "created_by",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields.copy()
        read_only_fields.remove("status")


class UserNotificationListWithCountSerializer(serializers.Serializer):
    """Serializer for user notification with count instance"""

    total_notifications = serializers.IntegerField(min_value=0, read_only=True)
    read_notifications = serializers.IntegerField(min_value=0, read_only=True)
    unread_notifications = serializers.IntegerField(min_value=0, read_only=True)
    notifications = NotificationSerializer(many=True, read_only=True)
    action_choice = serializers.ChoiceField(
        choices=NotificationsActionChoices.choices,
        default=NotificationsActionChoices.UNDEFINED,
        write_only=True,
    )
    notification_uids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, allow_null=True, required=False
    )

    def validate(self, attrs):
        action_choice = attrs.get("action_choice")
        notification_uids = attrs.get("notification_uids", [])

        if (
            action_choice
            in [
                NotificationsActionChoices.MARK_AS_READ,
                NotificationsActionChoices.MARK_AS_REMOVED,
            ]
            and not notification_uids
        ):
            raise serializers.ValidationError(
                {"notification_uids": "Notification uids are required"}
            )

        return attrs

    def update(self, instance, validated_data):
        from notifications.utils import (
            update_notification_read_status,
            update_notification_status,
        )

        action_choice = validated_data.get("action_choice")
        notifications = instance["notifications"]
        notification_uids = validated_data.get("notification_uids", [])
        user = self.context["request"].user

        # Mark all as read
        if action_choice == NotificationsActionChoices.MARK_ALL_AS_READ:
            # Update all notifications as read status
            notifications = (
                Notification()
                .get_active_notifications()
                .filter(
                    user=user,
                    is_read=False,
                )
            )
            update_notification_read_status(notifications=notifications)

        # Mark as read all selected notifications
        elif action_choice == NotificationsActionChoices.MARK_AS_READ:
            # Update selected notifications as read
            notifications = (
                Notification()
                .get_active_notifications()
                .filter(uid__in=notification_uids, is_read=False)
            )
            update_notification_read_status(notifications=notifications)

        # Removed all notifications
        elif action_choice == NotificationsActionChoices.REMOVED_ALL:
            # Remove all notifications
            notifications = Notification().get_active_notifications().filter(user=user)
            update_notification_status(
                notifications=notifications, status=NotificationsStatus.REMOVED
            )

        # Mark as removed all selected notifications
        elif action_choice == NotificationsActionChoices.MARK_AS_REMOVED:
            # Remove selected notifications
            notifications = (
                Notification()
                .get_active_notifications()
                .filter(uid__in=notification_uids)
            )
            update_notification_status(
                notifications=notifications, status=NotificationsStatus.REMOVED
            )

        return validated_data
