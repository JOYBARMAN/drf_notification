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




# Create your views here.
from rest_framework import generics
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from notifications.service import NotificationService
from notifications.utils import create_notification_json, get_changed_fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notifications.models import Notification
from django.db.models import QuerySet
from django.db.models.signals import post_save
from notifications.tasks import call_signal

User = get_user_model()


class NotCreateAPIView(APIView):
    """Create notification"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        self.user_list = User.objects.filter()
        notification_json = create_notification_json(
            message="Hello, World!",
            instance=request.user,
            method="POST",
            serializer=None,
            changed_data={},
        )
        notifications=Notification.objects.bulk_create(
            [
                Notification(
                    user=user,
                    notification=notification_json,
                    created_by=request.user,
                )
                for user in self.user_list
            ]
        )

        call_signal.apply_async(kwargs={"notification_ids": [instance.id for instance in notifications]})

        return Response({"message": "Notification created successfully."}, status=201)
