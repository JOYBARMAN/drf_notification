from django.urls import path

from notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/ac/notifications/me/", NotificationConsumer.as_asgi()),
]