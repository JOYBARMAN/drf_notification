"""Views for notification"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer


class UserNotificationList(generics.ListAPIView):
    """Views for user notification list"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationListWithCountSerializer

    def get_queryset(self):
        try:
            return [Notification().get_current_user_notifications()]
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
