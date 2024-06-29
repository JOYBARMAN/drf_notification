"""Views for notification"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound

from notifications.models import Notification
from notifications.serializers import (
    UserNotificationListWithCountSerializer,
    NotificationSerializer,
)
from notifications.paginations import CustomPagination


class UserNotificationList(generics.RetrieveUpdateAPIView):
    """Views for user notification list"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationListWithCountSerializer
    pagination_class = CustomPagination

    def get_object(self):
        try:
            queryset = Notification().get_current_user_notifications(
                user=self.request.user
            )
            notifications = queryset["notifications"].all()

            # Apply filter for is_read or unread notifications
            query_params = self.request.query_params.get("is_read")
            acceptable_value = {"true": True, "false": False}
            if query_params:
                query_params = acceptable_value.get(query_params.lower())

            # If valid query params found then filter
            if isinstance(query_params, bool):
                notifications = notifications.filter(is_read=query_params)

            # Paginate the notifications list
            paginator = CustomPagination()
            paginated_notifications = paginator.paginate_queryset(
                notifications, self.request
            )

            # Add pagination data to the response
            paginated_response = paginator.get_paginated_response(
                paginated_notifications
            )
            queryset["notifications"] = paginated_response.data["results"]

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
                .get_current_user_notifications(user=self.request.user)["notifications"]
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
