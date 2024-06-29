import json
import logging

from django.contrib.auth import get_user_model

from notifications.utils import (
    get_serialized_notifications,
    get_user,
    validate_token,
    get_group_name,
)

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get token from the URL
        token = self.scope["url_route"]["kwargs"].get("access_token")

        if token:
            user_id = validate_token(token=token)
            if not user_id:
                await self.close()
                return
        else:
            # Token not found in the URL
            await self.close()
            return

        user = await get_user(user_id)

        if user:
            self.scope["user"] = user
            self.scope["token"] = token

            # Add user to group
            self.group_name = get_group_name(user=user)
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )

            # Accept connection
            await self.accept()

        else:
            # User not found
            await self.close()

    async def receive(self, text_data=None):
        user = self.scope.get("user")
        token_valid = validate_token(token=self.scope.get("token"))

        # Return error message if token or user is invalid
        if not token_valid:
            await self.send(
                text_data=json.dumps({"error": "Token may be invalid or expired"})
            )
            return

        if not user:
            await self.send(text_data=json.dumps({"error": "User not authenticated"}))
            return

        notifications = await database_sync_to_async(get_serialized_notifications)(
            user=user
        )
        await self.send(text_data=json.dumps(notifications))

    async def disconnect(self, close_code):
        # Remove user from the group
        if self.scope.get("user"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

        self.close()
        logger.warning(f"disconnected {close_code}")

    async def notification_update(self, event):
        # Update the user's notifications when any change occurs in the Notification model
        user = self.scope.get("user")
        if user:
            notifications = event["user_notifications"]
            await self.send(text_data=json.dumps(notifications))
