import uuid

from django.db import transaction
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.db.models import Count, When, Case

from notifications.choices import NotificationsStatus

from dirtyfields import DirtyFieldsMixin


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
    """Notification model to store user notifications."""

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
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        db_index=True,
        related_name="user_notification_created_by",
        help_text="The user who created this notification.",
    )
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
        Perform this action before saving the model instance.
        """
        from notifications.utils import validate_notification

        super().clean()
        validate_notification(notification_data=self.notification, use_for_model=True)

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

        if not user:
            raise ValueError("User is missing.")

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

    def get_current_user_unread_notifications(self, user):
        """
        Retrieve unread notifications of current user.

        Returns:
            QuerySet: A queryset of unread notifications of current user.
        """
        return (
            Notification()
            .get_current_user_notifications(user=user)["notifications"]
            .filter(is_read=False)
        )

    def get_current_user_read_notifications(self, user):
        """
        Retrieve read notifications of current user.

        Returns:
            QuerySet: A queryset of read notifications of current user.
        """
        return (
            Notification()
            .get_current_user_notifications(user=user)["notifications"]
            .filter(is_read=True)
        )

    def create_notification_for_users(
        self, notification_data: dict, users: QuerySet, requested_user, **kwargs
    ):
        """Create notifications for multiple users efficiently."""
        from notifications.utils import validate_notification

        # Validate notification data
        validate_notification(notification_data=notification_data)

        # If users is a single user instance, convert it to a queryset
        if not isinstance(users, QuerySet):
            users = QuerySet(model=User).filter(id=users.id)

        # Create notification instances for each user
        notification_instance = [
            Notification(
                user=user,
                notification=notification_data,
                created_by=requested_user,
                **kwargs,
            )
            for user in users
        ]
        for notification in notification_instance:
            notification.save()

        return


class NotificationSettings(BaseModel):
    """Model to store user notification settings."""

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
        """Check if notifications are enabled for the user"""
        try:
            return self.__class__.objects.get(user=user).is_enable_notification
        except self.__class__.DoesNotExist:
            raise ValueError("Notification settings instance missing for this user")
