from django.db.models import TextChoices


class NotificationsStatus(TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    DRAFT = "DRAFT", "DRAFT"
    REMOVED = "REMOVED", "Removed"
    DELETED = "DELETED", "Deleted"