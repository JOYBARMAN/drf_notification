import uuid
import jsonschema

from django.db import transaction
from django.db import models
from django.contrib.auth import get_user_model
from django_currentuser.db.models import CurrentUserField
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.db.models import Count, When, Case

from notifications.choices import NotificationsStatus
from notifications.schema_validations import NOTIFICATION_SCHEMA

from dirtyfields import DirtyFieldsMixin
from jsonschema import validate

User = get_user_model()


class BaseModel(DirtyFieldsMixin, models.Model):
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

    def get_current_user_notifications(self, user):
        """
        Retrieve notifications for the current user if notifications are enabled.

        Returns:
            QuerySet: A queryset of notifications, total, read and unread notifications count belonging to the current user.

        Raises:
            ValueError: If notifications are not enabled for the current user.
        """

        if NotificationSettings().is_user_enable_notification(user=user):
            user_notifications = (
                Notification()
                .get_active_notifications()
                .filter(user=user)
                .select_related("user", "created_by")
            )
            # Aggregate the counts
            notification_counts = user_notifications.aggregate(
                total_notifications=Count("id"),
                read_notifications=Count(Case(When(is_read=True, then=1))),
            )

            return {
                "notifications": user_notifications,
                "total_notifications": notification_counts["total_notifications"],
                "read_notifications": notification_counts["read_notifications"],
                "unread_notifications": notification_counts["total_notifications"]
                - notification_counts["read_notifications"],
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
    def create_notifications(cls, notification, users, **kwargs):
        """
        Create notifications for multiple users efficiently.

        Args:
            notification (dict): Dictionary containing notification details.
            users (list, QuerySet, or User): Users for whom notifications will be created.
            **kwargs: Additional keyword arguments to be passed to the Notification model.

        Returns:
            dict: A dictionary containing created notifications and missing users.

        Raises:
            ValueError: If users parameter is not a list, QuerySet, or User.
            ValueError: If notification object does not contain required keys.

        Note:
            This method efficiently creates notifications for multiple users using bulk_create.
            It checks if the notification object contains required keys ('message' and 'object').
            It then creates notifications for each user found in the database, using bulk_create
            to insert them in a single query. It returns a dictionary containing the created
            notifications and any missing users not found in the database.
        """

        # Check if users is a single User object and convert it to a list
        if isinstance(users, User):
            users = [users]

        if not isinstance(users, (list, QuerySet)):
            raise ValueError("Users must be a list, QuerySet, or a User object")

        # Check if notification contains required keys
        required_keys = ["message", "object"]
        if not all(key in notification for key in required_keys):
            raise ValueError(
                "Notification object must contain required keys: {}".format(
                    ", ".join(required_keys)
                )
            )

        # Convert list of users to QuerySet if necessary
        if isinstance(users, list):
            user_ids = [user.id for user in users]
            user_queryset = User.objects.filter(id__in=user_ids)
        else:
            user_queryset = users

        # Get IDs of users found in the database
        found_user_ids = set(user_queryset.values_list("id", flat=True))

        # Find missing user IDs
        if isinstance(users, list):
            all_user_ids = {user.id for user in users}
        else:
            all_user_ids = set(users.values_list("id", flat=True))

        missing_user_ids = all_user_ids - found_user_ids

        # Create a list of Notification objects for each user
        notifications_to_create = []
        for user in user_queryset:
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
            "missing_users": User.objects.filter(id__in=missing_user_ids),
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

    def is_user_enable_notification(self, user):
        try:
            return self.__class__.objects.get(user=user).is_enable_notification
        except self.__class__.DoesNotExist:
            raise ValueError("Notification settings instance missing for this user")
