from django.db.models import TextChoices


class NotificationsStatus(TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    DRAFT = "DRAFT", "DRAFT"
    REMOVED = "REMOVED", "Removed"
    DELETED = "DELETED", "Deleted"


class NotificationsActionChoices(TextChoices):
    UNDEFINED = "UNDEFINED", "Undefined"
    MARK_ALL_AS_READ = "MARK_ALL_AS_READ", "Mark_All_As_Read"
    MARK_AS_READ = "MARK_AS_READ", "Mark_As_Read"
    REMOVE_ALL = "REMOVE_ALL", "Remove_All"
