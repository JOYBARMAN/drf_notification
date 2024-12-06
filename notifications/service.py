from django.db.models import QuerySet

from notifications.models import Notification
from notifications.utils import (
    create_notification_json,
    get_changed_fields,
    get_current_user,
)

from typing import Optional, List, Dict, Union


class NotificationService:
    """
    Service class for managing notifications.

    Provides methods for creating and retrieving notifications
    with encapsulated business logic for the notification system.
    """

    def __init__(
        self,
        requested_user=None,
        message: Optional[str] = None,
        instance=None,
        method: Optional[str] = None,
        user_list: Optional[List] = None,
        serializer=None,
    ):
        """
        Initialize the NotificationService.

        Args:
            requested_user: The user making the request (defaults to current user).
            message: The notification message.
            instance: The model instance associated with the notification.
            method: The HTTP method or action triggering the notification.
            user_list: A list of users to notify.
            serializer: A serializer instance for serializing data.
        """
        self.requested_user = requested_user or get_current_user()
        self.message = message
        self.instance = instance
        self.method = method.upper() if method else "UNDEFINED"
        self.user_list = user_list or []
        self.serializer = serializer

    def get_requested_user_notifications(self) -> Union[QuerySet, Dict[str, str]]:
        """
        Retrieve notifications for the requested user.

        Returns:
            QuerySet or dict: Notifications or error information.
        """
        try:
            return Notification().get_current_user_notifications(
                user=self.requested_user
            )
        except Exception as e:
            return {"error": f"Failed to retrieve notifications: {str(e)}"}

    def create_notification(self) -> Dict[str, str]:
        """
        Create a notification for the specified users.

        Raises:
            ValueError: If required arguments are missing.

        Returns:
            dict: Success or error message.
        """

        # Validate required arguments
        if not self.instance or not self.message or not self.user_list:
            raise ValueError(
                "Missing required arguments: 'instance', 'message', and 'user_list' must be provided."
            )

        try:
            # Prepare notification json
            notification_json = create_notification_json(
                message=self.message,
                instance=self.instance,
                method=self.method.upper() if self.method else "UNDEFINED",
                serializer=self.serializer,
                changed_data=(
                    get_changed_fields(self.instance)
                    if self.method.lower() in ["patch", "put"]
                    else {}
                ),
            )
            # Create notification for the users
            Notification().create_notification_for_users(
                notification_data=notification_json,
                users=self.user_list,
                requested_user=self.requested_user,
            )

            return {"success": "Notification created successfully"}

        except Exception as e:
            return {"error": f"Failed to create notification: {str(e)}"}

    def get_model_notifications(
        self, model_name: str
    ) -> Union[QuerySet, Dict[str, str]]:
        """
        Retrieve notifications for a specific model.

        Args:
            model_name: The name of the model.

        Returns:
            QuerySet or dict: Notifications or error information.
        """
        try:
            return Notification.objects.filter(notification__model=model_name.title())
        except Exception as e:
            return {"error": f"Failed to retrieve model notifications: {str(e)}"}
