"""Views for notification"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound

from notifications.models import Notification
from notifications.serializers import (
    UserNotificationListWithCountSerializer,
    NotificationSerializer,
)


class UserNotificationList(generics.RetrieveAPIView):
    """Views for user notification list"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationListWithCountSerializer

    def get_object(self):
        try:
            queryset = Notification().get_current_user_notifications()

            # Apply filter for is_read or unread notifications
            query_params = self.request.query_params.get("is_read")
            acceptable_value = {
                "true":True,
                "false":False
            }
            if query_params:
                query_params = acceptable_value.get(query_params.lower())

            # If valid query params then filter
            if isinstance(query_params, bool):
                queryset["notifications"]= queryset["notifications"].filter(is_read=query_params)

            return queryset

        except ValueError as e:
            raise ValidationError({"detail": str(e)})


class UserNotificationDetail(generics.RetrieveUpdateAPIView):
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
