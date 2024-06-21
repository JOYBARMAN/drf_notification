from django.urls import path
from notifications.consumers import EchoConsumer

websocket_urlpatterns = [
    path("ws/sc/", EchoConsumer.as_asgi()),
]