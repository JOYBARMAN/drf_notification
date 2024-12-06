import json
import logging

from django.contrib.auth import get_user_model

from notifications.utils import (
    get_user_serialized_notifications,
    get_user,
    get_group_name,
)

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Accept connection
        await self.accept()

        if self.is_error_exists():
            error = {"error": str(self.scope["error"])}
            await self.send(text_data=json.dumps(error))
            await self.close()
            return

        # Get the user_id from the scope
        user_id = self.scope.get("user_id")

        # Get the user instance
        user = await get_user(user_id)
        if not user:
            user_error = {"error": "User not found"}
            await self.send(text_data=json.dumps(user_error))
            await self.close()
            return

        # Add user to the scope
        self.scope["user"] = user

        # Add user to group
        self.group_name = get_group_name(user=user)
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        # Send the user's notifications
        await self.receive()

    async def receive(self, text_data=None):
        user = self.scope.get("user")

        try:
            # Get the user's notifications
            notifications = await database_sync_to_async(get_user_serialized_notifications)(
                user=user
            )
        except ValueError as e:
            # Handle the error when user not enabled the notification settings
            await self.send(text_data=json.dumps({"error": str(e)}))
            return

        await self.send(text_data=json.dumps(notifications))

    async def disconnect(self, close_code):
        # Remove user from the group
        if self.scope.get("user"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )
            logger.warning(f"disconnected {close_code}")

        await self.close()

    async def notification_update(self, event):
        # Update the user's notifications when any change occurs in the Notification model
        user = self.scope.get("user")
        if user:
            notifications = event["user_notifications"]
            await self.send(text_data=json.dumps(notifications))

    def is_error_exists(self):
        # Checks if error exists during websockets
        return True if "error" in self.scope else False
