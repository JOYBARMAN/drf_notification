from . import urlhelpers, test_helpers, base_test

from config.asgi import application
from channels.testing import WebsocketCommunicator


class TestNotificationWebSocketApi(base_test.BaseTest):
    """Test case for notification consumer is working properly or not"""

    def setUp(self):
        super().setUp()

    async def test_connect_notification_consumer(self):
        """Connect to notification consumer"""

        # Generate user token
        access_token = await test_helpers.get_user_token(self.user)
        bearer_token = f"Bearer {access_token.get('access')}"

        ws_url = urlhelpers.get_notification_ws_url()

        # Initialize WebSocket communicator
        communicator = WebsocketCommunicator(
            application,
            ws_url,
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

        return communicator

    async def test_receive_notification_consumer(self):
        """Receive notification from consumer"""

        communicator = await self.test_connect_notification_consumer()

        # Receive a message from the WebSocket and check its content
        response = await communicator.receive_json_from()

        self.assertIn("total_notifications", response) and self.assertEqual(
            response["total_notifications"], self.total_created_notification
        )
        self.assertIn("unread_notifications", response) and self.assertEqual(
            response["unread_notifications"], self.total_created_notification
        )
        self.assertIn("read_notifications", response) and self.assertEqual(
            response["read_notifications"],
            response["total_notifications"] - response["unread_notifications"],
        )

    async def test_disconnect_notification_consumer(self):
        """Disconnect to notification consumer"""

        communicator = await self.test_connect_notification_consumer()

        # Disconnect from the WebSocket
        await communicator.disconnect()
