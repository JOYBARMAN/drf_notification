from django.db.models import Count, Case, When
from django.contrib.auth import get_user_model
from django.core.cache import cache

from notifications.models import NotificationSettings, Notification

from celery import shared_task


User = get_user_model()


@shared_task
def call_signal(notification_ids):
    """Call the notification signal."""
    from notifications.models import Notification

    all_isinstances = Notification.objects.filter(id__in=notification_ids)
    for instance in all_isinstances:
        instance.save()


@shared_task
def cached_user_notifications(user_id):

    user = User.objects.filter(id=user_id).first()

    if not user:
        raise ValueError("User is missing.")

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
    cache_key = f"notifications_{user_id}"
    cache.set(cache_key, {"user_notifications": user_notifications, "notification_counts": notification_counts})
