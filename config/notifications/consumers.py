import json
import logging

from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import AccessToken

from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get token from the URL
        token = self.scope["url_route"]["kwargs"].get("access_token")

        if token:
            user_id = self.validate_token(token)
            if not user_id:
                await self.close()
                return
        else:
            # Token not found in the URL
            await self.close()
            return

        user = await self.get_user(user_id)

        if user:
            self.scope["user"] = user
            self.scope["token"] = token
            await self.accept()
        else:
            # User not found
            await self.close()

    def validate_token(self, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token.payload["user_id"]
            return user_id
        except Exception as e:
            logger.error(f"{e}")
            return None

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User not found")
            return None

    @database_sync_to_async
    def get_notifications(self, user):
        notifications = Notification().get_current_user_notifications(user=user)
        serialized_data = UserNotificationListWithCountSerializer(notifications).data
        return serialized_data

    async def receive(self, text_data=None):
        user = self.scope.get("user")
        token_valid = self.validate_token(self.scope.get("token"))

        if not token_valid:
            await self.send(
                text_data=json.dumps({"error": "Token may be invalid or expired"})
            )
            return

        if not user:
            await self.send(text_data=json.dumps({"error": "User not authenticated"}))
            return

        notifications = await self.get_notifications(user=user)
        await self.send(text_data=json.dumps(notifications))

    async def disconnect(self, close_code):
        logger.warning(f"disconnected {close_code}")
        self.close()
