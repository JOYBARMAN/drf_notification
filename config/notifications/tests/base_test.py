from rest_framework.test import APITestCase, APIClient

from notifications.serializers import get_user_serializer
from . import payloads, test_helpers

from asgiref.sync import async_to_sync


class BaseTest(APITestCase):
    """Create a base test class to use multiple places"""

    def setUp(self):
        # Set up a test client
        self.client = APIClient()

        # Define user payload
        self.user_payload = payloads.user1_payload()

        # Create a user
        self.user = async_to_sync(test_helpers.create_user)(**self.user_payload)
        self.user2 = async_to_sync(test_helpers.create_user)(**payloads.user2_payload())

        # Get user list
        self.user_list = test_helpers.get_user_list()

        # Get token for user
        self.user_token = async_to_sync(test_helpers.get_user_token)(self.user)

        # Set token for user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.user_token["access"],
        )

        # Define notification message ,number of notification
        self.total_created_notification = 10
        self.notification_message = payloads.notification_message_payload(
            total=self.total_created_notification
        )

        # Create notification for user
        self.notification = self.create_notification()

    def create_notification(self):
        """Create notification for user"""
        test_helpers.create_notification(
            model_data=self.user,
            serializer=get_user_serializer(),
            user_list=self.user_list,
            notification_message=self.notification_message,
            requested_user=self.user,
        )
        return
