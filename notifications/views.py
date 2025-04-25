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
from notifications.utils import (
    get_user_cache_notifications,
    set_user_notifications_in_cache,
)


class UserNotificationList(generics.RetrieveUpdateAPIView):
    """Views for user notification list"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationListWithCountSerializer
    pagination_class = CustomPagination

    def get_object(self):
        try:
            # Get user, query parameters, and page number
            user = self.request.user
            query_params = self.request.query_params.get("is_read")
            page_number = self.request.query_params.get("page", 1)

            # Modify query params
            acceptable_value = {"true": True, "false": False}
            if query_params:
                query_params = acceptable_value.get(query_params.lower())

            # Try to get user notifications from the cache
            user_cached_notifications = get_user_cache_notifications(
                user=user, page_number=page_number, query_params=query_params
            )
            if user_cached_notifications:
                return user_cached_notifications

            # Retrieve notifications from the database
            queryset = Notification().get_current_user_notifications(user=user)
            notifications = queryset["notifications"].all()

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

            # Update the user's cache
            set_user_notifications_in_cache(
                user=user,
                page_number=page_number,
                query_params=query_params,
                queryset=queryset,
            )

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
                notification.save()

            return notification

        except ValueError as e:
            raise ValidationError({"detail": str(e)})
