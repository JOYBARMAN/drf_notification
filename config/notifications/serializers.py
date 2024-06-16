"""Serializer for notification related """

from django.contrib.auth import get_user_model

from rest_framework import serializers

from notifications.models import Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
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

    user = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
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

    total_notifications = serializers.IntegerField(min_value=0)
    read_notifications = serializers.IntegerField(min_value=0)
    unread_notifications = serializers.IntegerField(min_value=0)
    notifications = NotificationSerializer(many=True)
