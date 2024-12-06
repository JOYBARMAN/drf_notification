from django.contrib import admin

from notifications.models import Notification, NotificationSettings


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "is_read", "created_at", "updated_at")
    list_filter = ("user", "is_read", "status", "created_at", "updated_at")
    search_fields = ("user__username", "notification")
    readonly_fields = ("uid", "created_at", "updated_at")


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enable_notification")
    list_filter = ("user", "is_enable_notification")
    search_fields = ("user__username",)
    readonly_fields = ("uid", "created_at", "updated_at")
