from django.urls import path
from notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/ac/notifications/me/<str:access_token>/", NotificationConsumer.as_asgi()),
]