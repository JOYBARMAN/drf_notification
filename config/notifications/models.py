import uuid
import jsonschema

from django.db import transaction
from django.db import models
from django.contrib.auth import get_user_model
from django_currentuser.db.models import CurrentUserField
from django_currentuser.middleware import (
    get_current_user,
    get_current_authenticated_user,
)
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet

from notifications.choices import NotificationsStatus
from notifications.schema_validations import NOTIFICATION_SCHEMA

from jsonschema import validate

User = get_user_model()


class BaseModel(models.Model):
    """Base class for all other models."""

    # Unique identifier.
    uid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        unique=True,
        help_text="Unique identifier for this model instance.",
    )
    # Timestamp indicating when the instance was created.
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp indicating when the instance was created.",
    )
    # Timestamp indicating when the instance was last updated.
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp indicating when the instance was last updated.",
    )

    class Meta:
        abstract = True


class CustomNotificationField(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def extend_notification_model(cls, notification_model):
        """
        Extend the notification model with custom fields.

        Args:
            notification_model (django.db.models.Model): The notification model to extend.

        Notes:
            This method dynamically adds custom fields from the CustomNotificationField
            class to the provided notification_model.
        """
        # Get all fields from the custom field class
        custom_fields = cls._meta.fields

        # Add each custom field to the Notification model
        for field in custom_fields:
            field.contribute_to_class(notification_model, field.name)


class Notification(BaseModel):
    # The user associated with this notification.
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="user_notification",
        help_text="The user to whom this notification belongs.",
    )
    # JSON field to store the notification data.
    notification = models.JSONField(help_text="Notification data in JSON format.")
    # Indicates whether the notification has been read or not.
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indicates whether the notification has been read or not.",
    )
    # Additional custom information related to the notification.
    custom_info = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional custom information related to the notification.",
    )
    # The user who created this notification.
    created_by = CurrentUserField(help_text="The user who created this notification.")
    # Status of the notification (e.g., active, archived, deleted).
    status = models.CharField(
        max_length=20,
        choices=NotificationsStatus.choices,
        db_index=True,
        default=NotificationsStatus.ACTIVE,
        help_text="Status of the notification.",
    )

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        """
        Return a string representation of the notification.

        Returns:
            str: String representation of the notification.
        """
        return f"{self.user} - {self.notification.get('message', '')} - {self.is_read}"

    def clean(self):
        """
        Perform JSON schema validation for the notification field.
        """
        super().clean()

        try:
            validate(instance=self.notification, schema=NOTIFICATION_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise ValidationError({"notification": str(e)})

    def get_active_notifications(self):
        """
        Retrieve active notifications.

        Returns:
            QuerySet: A queryset of active notifications.
        """
        return self.__class__.objects.filter(
            status=NotificationsStatus.ACTIVE
        ).order_by("-pk")

    def get_current_user_notifications(self):
        """
        Retrieve notifications for the current user if notifications are enabled.

        Returns:
            QuerySet: A queryset of notifications, total, read and unread notifications count belonging to the current user.

        Raises:
            ValueError: If notifications are not enabled for the current user.
        """

        if NotificationSettings().is_user_enable_notification():
            user_notifications = (
                Notification()
                .get_active_notifications()
                .filter(user=get_current_authenticated_user())
                .select_related("user", "created_by")
            )
            return {
                "notifications": user_notifications,
                "total_notifications": int(user_notifications.count()),
                "read_notifications": int(
                    user_notifications.filter(is_read=True).count()
                ),
                "unread_notifications": int(
                    user_notifications.filter(is_read=False).count()
                ),
            }
        else:
            raise ValueError("Notifications are not enabled for the current user.")

    def get_current_user_unread_notifications(self):
        """
        Retrieve unread notifications of current user.

        Returns:
            QuerySet: A queryset of unread notifications of current user.
        """
        return (
            Notification()
            .get_current_user_notifications()["notifications"]
            .filter(is_read=False)
        )

    def get_current_user_read_notifications(self):
        """
        Retrieve read notifications of current user.

        Returns:
            QuerySet: A queryset of read notifications of current user.
        """
        return (
            Notification()
            .get_current_user_notifications()["notifications"]
            .filter(is_read=True)
        )

    @classmethod
    def create_notifications(cls, notification, *users, **kwargs):
        """
        Create notifications for multiple users efficiently.

        Args:
            notification (dict): Dictionary containing notification details.
            *users (list or QuerySet): Users for whom notifications will be created.
            **kwargs: Additional keyword arguments to be passed to the Notification model.

        Returns:
            dict: A dictionary containing created notifications and missing users.

        Raises:
            ValueError: If users parameter is not a list or QuerySet.
            ValueError: If notification object does not contain required keys.

        Note:
            This method efficiently creates notifications for multiple users using bulk_create.
            It checks if the notification object contains required keys ('message' and 'object').
            It then creates notifications for each user found in the database, using bulk_create
            to insert them in a single query. It returns a dictionary containing the created
            notifications and any missing users not found in the database.

        """
        if not isinstance(users, (list, QuerySet)):
            raise ValueError("Users must be a list or QuerySet")

        # Check if notification contains required keys
        required_keys = ["message", "object"]
        if not all(key in notification for key in required_keys):
            raise ValueError(
                "Notification object must contain required keys: {}".format(
                    ", ".join(required_keys)
                )
            )

        # Convert *users arguments into a single queryset
        user_ids = [user.id for user in users]
        user_queryset = User.objects.filter(id__in=user_ids)

        # Get IDs of users found in the database
        found_user_ids = set(user_queryset.values_list("id", flat=True))

        # Find missing user IDs
        missing_user_ids = set(user_ids) - found_user_ids

        found_user = user_queryset.filter(id__in=found_user_ids)

        # Create a list of Notification objects for each user
        notifications_to_create = []
        for user in found_user:
            notifications_to_create.append(
                Notification(user=user, notification=notification, **kwargs)
            )

        # Use bulk_create to insert notifications into the database in a single query
        with transaction.atomic():
            created_notifications = Notification.objects.bulk_create(
                notifications_to_create
            )

        return {
            "created_notifications": created_notifications,
            "missing_user": user.filter(id__in=missing_user_ids),
        }


class NotificationSettings(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="notification_settings",
        verbose_name="User",
    )
    is_enable_notification = models.BooleanField(
        default=True, verbose_name="Enable Notifications"
    )

    class Meta:
        verbose_name = "Notification Setting"
        verbose_name_plural = "Notification Settings"

    def __str__(self):
        """
        Return a string representation of the notification settings

        Returns:
            str: String representation of the notification settings
        """
        return f"{self.user.username} - Notifications Enabled: {self.is_enable_notification}"

    def is_user_enable_notification(self):
        return self.__class__.objects.get(
            user=get_current_authenticated_user()
        ).is_enable_notification


# Automatically extend Notification model with custom fields
CustomNotificationField.extend_notification_model(Notification)
