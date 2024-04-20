# Generated by Django 5.0.3 on 2024-04-20 19:50

import django.db.models.deletion
import django_currentuser.db.models.fields
import django_currentuser.middleware
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='Unique identifier for this notification.', unique=True)),
                ('notification', models.JSONField(help_text='Notification data in JSON format.')),
                ('is_read', models.BooleanField(db_index=True, default=False, help_text='Indicates whether the notification has been read or not.')),
                ('custom_info', models.JSONField(blank=True, help_text='Additional custom information related to the notification.', null=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('DRAFT', 'DRAFT'), ('REMOVED', 'Removed'), ('DELETED', 'Deleted')], db_index=True, default='ACTIVE', help_text='Status of the notification.', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp indicating when the notification was created.')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Timestamp indicating when the notification was last updated.')),
                ('created_by', django_currentuser.db.models.fields.CurrentUserField(default=django_currentuser.middleware.get_current_authenticated_user, help_text='The user who created this notification.', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(help_text='The user to whom this notification belongs.', on_delete=django.db.models.deletion.CASCADE, related_name='user_notification', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
            },
        ),
    ]
