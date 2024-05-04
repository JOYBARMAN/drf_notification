"""Url mapping for notification"""

from django.urls import path

from notifications.views import UserNotificationList

urlpatterns = [
    path("user", UserNotificationList.as_view(), name="user-notification-list"),
]
