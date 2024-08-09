from django.test import TestCase

from config.asgi import application

from .test_helpers import create_user, get_user_token
from .payloads import user_payload

from channels.testing import WebsocketCommunicator


class WebSocketNotificationTests(TestCase):
    async def test_notification_consumer(self):
        # Create user
        user = await create_user(**user_payload())

        # Generate user token
        access_token = await get_user_token(user)
        bearer_token = f"Bearer {access_token.get('access')}"

        # Initialize WebSocket communicator
        communicator = WebsocketCommunicator(
            application,
            "/ws/ac/me/notifications/",
            headers=[
                (
                    b"authorizations",
                    bearer_token.encode("utf-8"),
                )
            ],
        )

        # Connect to the WebSocket
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send a message to the WebSocket
        await communicator.send_json_to({"type": "test.message"})

        # Receive a message from the WebSocket and check its content
        response = await communicator.receive_json_from()
        self.assertIn("total_notifications", response)
        self.assertIn("read_notifications", response)
        self.assertIn("unread_notifications", response)

        # Close the WebSocket connection
        await communicator.disconnect()
