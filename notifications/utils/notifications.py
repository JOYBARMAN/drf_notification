import json, jsonschema, math

from django.conf import settings
from django.core import serializers
from django.core.paginator import Paginator, EmptyPage
from django.db import models
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict

from rest_framework.exceptions import ValidationError

from notifications.choices import NotificationsStatus
from notifications.utils.schema_validations import NOTIFICATION_SCHEMA
from notifications.utils.cache import (
    set_user_notifications_in_cache,
    get_user_cache_notifications,
)
from notifications.models import Notification
from notifications.serializers import UserNotificationListWithCountSerializer


# Get the settings
ALLOWED_NOTIFICATION_DATA = getattr(settings, "ALLOWED_NOTIFICATION_DATA", True)


def create_notification_json(
    message: str = None,
    instance: QuerySet = None,
    serializer=None,
    method="UNDEFINED",
    changed_data: dict = {},
):
    """Create a notification field json data for notification model"""

    # Handle the required fields error
    required_fields = {"message": message, "instance": instance}
    for field_name, field_value in required_fields.items():
        if not field_value:
            raise ValidationError(f"{field_name} is required for notification")

    # Serialize the queryset/model to JSON
    if serializer:
        serialized_model = serializer(instance).data
    else:
        serialized_model = json.loads(serializers.serialize("json", [instance]))[0]

    # Arrange the notification object
    notification = {
        "message": message,
        "model": instance.__class__.__name__,
        "instance": serialized_model,
        "method": method,
        "changed_data": changed_data,
    }

    # Validate the notification against the schema
    validate_notification(notification)

    return notification


def validate_notification(notification_data: dict, use_for_model=False):
    """
    Perform JSON schema validation for the notification field.
    """
    from django.core.exceptions import ValidationError

    try:
        jsonschema.validate(instance=notification_data, schema=NOTIFICATION_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        # Create a readable message for notification message
        valid_schema_message = {
            "message": "Your Message you want to send in notification",
            "instance": {"Model instance, which model is responsible for notification"},
        }
        message = f"Notification object must be a valid JSON schema such as {valid_schema_message}"

        # If the validation is for model then raise ValidationError
        if use_for_model:
            raise ValidationError(message)

        raise ValueError(message)


def serialized_notifications(notifications):
    """Serialize the notifications"""
    return UserNotificationListWithCountSerializer(notifications).data


def get_user_serialized_notifications(user, is_read: str = "", page=1, page_size=25):
    """Get notifications for the user and return serialized data with pagination"""
    # Modify is _read to boolean
    acceptable_value = {"true": True, "false": False}
    is_read = (
        is_read
        if isinstance(is_read, bool)
        else acceptable_value.get(is_read.lower(), None)
    )

    # Try to get user notifications from the cache
    user_cached_notifications = get_user_cache_notifications(
        user=user,
        page_number=page,
        query_params=is_read,
    )
    if user_cached_notifications:
        queryset = user_cached_notifications
    else:
        # Retrieve notifications from the database
        try:
            queryset = Notification().get_current_user_notifications(user=user)
            notifications = queryset["notifications"].all()
        except ValueError as e:
            return {"error": str(e)}

        # If valid query params found then filter
        if isinstance(is_read, bool):
            notifications = notifications.filter(is_read=is_read)

        # Paginate the notifications list
        paginator = Paginator(notifications, page_size)

        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            queryset["notifications"] = [{"detail": "Invalid page number."}]
            return get_paginate_response(
                queryset=queryset,
                page=page,
                page_size=page_size,
            )

        # Add pagination data to the response
        queryset["notifications"] = page_obj.object_list

        # Update the user's cache
        set_user_notifications_in_cache(
            user=user,
            page_number=page,
            query_params=is_read,
            queryset=queryset,
        )

    serialized_notification = serialized_notifications(queryset)

    return get_paginate_response(
        queryset=serialized_notification,
        page=page,
        page_size=page_size,
    )


def get_paginate_response(queryset, page=1, page_size=25):
    """Get paginated response for a queryset"""
    return {
        "results": queryset,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(queryset["total_notifications"] / page_size),
            "total_items": queryset["total_notifications"],
        },
    }


def update_notification_read_status(notifications, is_read=True):
    """Update the read status of the notifications"""
    for notification in notifications:
        notification.is_read = is_read

    # Update using bulk update
    return Notification.objects.bulk_update(notifications, ["is_read"])


def update_notification_status(notifications, status: NotificationsStatus):
    """Update the status of the notifications"""
    for notification in notifications:
        notification.status = status

    # Update using bulk update
    return Notification.objects.bulk_update(notifications, ["status"])


def get_changed_fields(model_instance):
    """
    Get changed fields of a model instance by comparing it with the original DB record.
    Handles ForeignKey, OneToOne, ManyToMany, and JSONField types.
    """
    changed_data = {}

    original_instance = model_instance.__class__.objects.filter(
        pk=model_instance.pk
    ).first()

    if not original_instance:
        raise ValueError("Model instance not found in the database.")

    for field in model_instance._meta.fields:
        name = field.name
        original_value = getattr(original_instance, name)
        current_value = getattr(model_instance, name)

        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            original_value = model_to_dict(original_value) if original_value else None
            current_value = model_to_dict(current_value) if current_value else None

        if isinstance(field, models.JSONField):
            json_changes = compare_json_fields(
                original_value or {}, current_value or {}
            )
            if json_changes:
                changed_data[name] = json_changes
            continue

        if original_value != current_value:
            changed_data[name] = {"original": original_value, "new": current_value}

    # Handle ManyToMany separately
    changed_data = compare_many_to_many_fields(
        changed_data, model_instance, original_instance
    )

    return changed_data


def compare_many_to_many_fields(changed_data, current_instance, original_instance):
    """
    Compare ManyToMany fields for added/removed items.
    """
    for field in current_instance._meta.many_to_many:
        name = field.name
        original_qs = getattr(original_instance, name).all()
        current_qs = getattr(current_instance, name).all()

        original_set = {tuple(sorted(obj.items())) for obj in original_qs.values()}
        current_set = {tuple(sorted(obj.items())) for obj in current_qs.values()}

        added = current_set - original_set
        removed = original_set - current_set

        if added or removed:
            changed_data[name] = {
                "original": list(original_qs.values()),
                "new": list(current_qs.values()),
                "added": list(added) if added else None,
                "removed": list(removed) if removed else None,
            }

    return changed_data


def compare_json_fields(original, current):
    """
    Compare two JSON-like dicts and return a dict with changed keys and their values.
    """
    changes = {
        key: {"original": original.get(key), "new": current.get(key)}
        for key in set(original) | set(current)
        if original.get(key) != current.get(key)
    }
    return changes or None
