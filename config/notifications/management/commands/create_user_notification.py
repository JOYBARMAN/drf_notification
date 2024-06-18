import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from faker import Faker
from tqdm import tqdm

from notifications.models import Notification, NotificationSettings


class Command(BaseCommand):
    help = "Create 1000 users and users notifications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--total", type=int, default=1000, help="Number of users to create"
        )

    def handle(self, *args, **kwargs):
        total = kwargs["total"]

        fake = Faker()

        default_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "password": "123456",
                "email": "admin@gmail.com",
            },
        )

        user_list = []

        for id in tqdm(range(total), desc="Creating users and user notifications"):
            user = User(
                username=f"{fake.user_name()}_{id}",
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password="password",
            )
            user.save()
            user_list.append(user)

        # Create user sample notification for user
        notification = {
            "message": "New Incomming Notification",
            "object": {"uid": "baebd6f0-be33-481f-894d-07f3404e87a5"},
        }
        kwargs = {"created_by": default_user}
        Notification().create_notifications(
            notification=notification, users=user_list, **kwargs
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created notifications for each user")
        )
