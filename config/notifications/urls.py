"""Url mapping for notification"""

from django.urls import path

from notifications import views

urlpatterns = [
    path("", views.UserNotificationList.as_view(), name="user-notification-list"),
    path("/<uuid:uid>", views.UserNotificationDetail.as_view(), name="user-notification-detail"),
]
