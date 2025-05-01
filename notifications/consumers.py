import json, logging

from django.contrib.auth import get_user_model

from notifications.utils.notifications import get_user_serialized_notifications
from notifications.utils.consumers import get_user, get_group_name

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the subprotocols from the scope
        subprotocols = self.scope.get("subprotocols")
        if subprotocols:
            await self.accept(subprotocol=subprotocols)
        else:
            await self.accept()

        # If token is invalid or missing
        if self.is_error_exists():
            error = self.scope.get("error")
            await self.send(text_data=json.dumps({"error": error}))
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
        # Extract the page and page_size from the received message
        data = json.loads(text_data or "{}")
        page = data.get("page", 1)
        page_size = data.get("page_size", 25)
        is_read = data.get("is_read", "")

        try:
            # Get the user's notifications
            notifications = await database_sync_to_async(
                get_user_serialized_notifications
            )(
                user=user,
                is_read=is_read,
                page=page,
                page_size=page_size,
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
            await self.receive()

    def is_error_exists(self):
        # Checks if error exists during websockets
        return True if "error" in self.scope else False
