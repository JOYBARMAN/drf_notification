from django.urls import reverse


def get_user_notification_list_url():
    return reverse("user-notification-list")


def get_notification_detail_url(uid: str):
    return reverse("user-notification-detail", args=[uid])


def get_notification_ws_url():
    return f"ws/ac/me/notifications/"
