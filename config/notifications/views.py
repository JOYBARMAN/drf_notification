"""Views for notification"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound

from notifications.models import Notification
from notifications.serializers import (
    UserNotificationListWithCountSerializer,
    NotificationSerializer,
)


class UserNotificationList(generics.ListAPIView):
    """Views for user notification list"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationListWithCountSerializer

    def get_queryset(self):
        try:
            return [Notification().get_current_user_notifications()]
        except ValueError as e:
            raise ValidationError({"detail": str(e)})


class UserNotificationDetail(generics.RetrieveAPIView):
    """Views for user notification list"""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_object(self):
        try:
            uid = self.kwargs.get("uid")

            # Get user notification single instance
            notification = (
                Notification()
                .get_current_user_notifications()["notifications"]
                .filter(uid=uid)
                .first()
            )
            if not notification:
                raise NotFound(detail="Notification not found")

            # Update unread notification
            if not notification.is_read:
                notification.is_read = True
                notification.save_dirty_fields()

            return notification

        except ValueError as e:
            raise ValidationError({"detail": str(e)})
