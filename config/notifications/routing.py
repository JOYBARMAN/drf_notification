from django.urls import path

from notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/ac/me/notifications/", NotificationConsumer.as_asgi()),
]