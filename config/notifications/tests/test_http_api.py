import json

from rest_framework import status

from notifications.choices import NotificationsActionChoices

from . import urlhelpers, base_test


class TestNotificationHTTPApi(base_test.BaseTest):
    """Test case for notification http api"""

    def setUp(self):
        super().setUp()

    def test_get_user_notifications(self):
        """Test case for get user notifications"""

        # Check user notification list endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_user_notification_list_url(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert response data countable values
        response_data = response.json()
        self.assertEqual(
            response_data["total_notifications"], self.total_created_notification
        )
        self.assertEqual(
            response_data["unread_notifications"], self.total_created_notification
        )
        self.assertEqual(
            response_data["read_notifications"],
            response_data["total_notifications"]
            - response_data["unread_notifications"],
        )

        # Check notification value
        notification_index = self.total_created_notification - 1
        self.assertEqual(
            response_data["notifications"][0]["notification"]["message"],
            self.notification_message[notification_index]["message"],
        )
        self.assertEqual(
            response_data["notifications"][0]["notification"]["method"],
            self.notification_message[notification_index]["method"],
        )

        # Check notification fields
        self.check_notification_fields(response_data["notifications"][0])

        return response_data

    def test_get_user_notification_detail(self):
        """Test case for get user notification detail"""

        notification_list = self.test_get_user_notifications()
        uid = notification_list["notifications"][0]["uid"]

        # Check user notification detail endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_notification_detail_url(uid),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data notification
        response_data = response.json()
        self.check_notification_fields(response_data)

        return response_data

    def test_updated_notifications_list_after_seen(self):
        """Test case for update notifications list count after see detail"""

        notification_detail = self.test_get_user_notification_detail()

        # Check user notification list endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_user_notification_list_url(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check is update notification read status
        notification_detail["is_read"] = True

        # Assert response data countable values
        response_data = response.json()
        self.assertEqual(response_data["read_notifications"], 1)
        self.assertEqual(
            response_data["total_notifications"], self.total_created_notification
        )
        self.assertEqual(
            response_data["unread_notifications"],
            self.total_created_notification - response_data["read_notifications"],
        )

    def test_removed_all_notifications(self):
        """Test case for remove all notifications"""

        payload = {"action_choice": NotificationsActionChoices.REMOVED_ALL}

        # Check user notification remove all and assert response status code
        response = self.client.patch(
            urlhelpers.get_user_notification_list_url(),
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check user notification list endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_user_notification_list_url(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data after remove all notifications
        response_data = response.json()
        self.assertEqual(response_data["total_notifications"], 0)
        self.assertEqual(response_data["read_notifications"], 0)
        self.assertEqual(response_data["unread_notifications"], 0)

    def test_mark_all_as_read_notifications(self):
        """Test case for mark all as read notifications"""

        payload = {"action_choice": NotificationsActionChoices.MARK_ALL_AS_READ}

        # Check user notification mark all as read and assert response status code
        response = self.client.patch(
            urlhelpers.get_user_notification_list_url(),
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check user notification list endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_user_notification_list_url(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data after mark all as read notifications
        response_data = response.json()
        self.assertEqual(
            response_data["total_notifications"], self.total_created_notification
        )
        self.assertEqual(
            response_data["read_notifications"], self.total_created_notification
        )
        self.assertEqual(response_data["unread_notifications"], 0)

    def test_mark_as_read_notifications(self):
        """Test case for mark as read notifications"""

        notification_list = self.test_get_user_notifications()
        uid = [
            notification["uid"]
            for notification in notification_list["notifications"][:5]
        ]

        payload = {
            "action_choice": NotificationsActionChoices.MARK_AS_READ,
            "notification_uids": uid,
        }

        # Check user notification mark as read and assert response status code
        response = self.client.patch(
            urlhelpers.get_user_notification_list_url(),
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check user notification list endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_user_notification_list_url(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data after mark as read notifications
        response_data = response.json()
        self.assertEqual(
            response_data["total_notifications"], self.total_created_notification
        )
        self.assertEqual(response_data["read_notifications"], len(uid))
        self.assertEqual(
            response_data["unread_notifications"],
            response_data["total_notifications"] - len(uid),
        )

    def test_mark_as_removed_notifications(self):
        """Test case for mark as removed notifications"""

        notification_list = self.test_get_user_notifications()
        uid = [
            notification["uid"]
            for notification in notification_list["notifications"][:5]
        ]

        payload = {
            "action_choice": NotificationsActionChoices.MARK_AS_REMOVED,
            "notification_uids": uid,
        }

        # Check user notification mark as removed and assert response status code
        response = self.client.patch(
            urlhelpers.get_user_notification_list_url(),
            json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check user notification list endpoint and assert response status code
        response = self.client.get(
            urlhelpers.get_user_notification_list_url(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data after mark as removed notifications
        response_data = response.json()
        self.assertEqual(
            response_data["total_notifications"],
            self.total_created_notification - len(uid),
        )
        self.assertEqual(
            response_data["unread_notifications"],
            self.total_created_notification - len(uid),
        )
        self.assertEqual(
            response_data["read_notifications"],
            response_data["total_notifications"]
            - response_data["unread_notifications"],
        )

    def check_notification_fields(self, notification):
        """Check some fields in notification data"""

        other_fields = [
            "id",
            "uid",
            "user",
            "is_read",
            "custom_info",
            "created_by",
            "status",
            "created_at",
            "updated_at",
        ]
        for field in other_fields:
            self.assertIn(field, notification)

        return notification
