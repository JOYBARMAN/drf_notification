from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import RefreshToken

from channels.db import database_sync_to_async


@database_sync_to_async
def create_user(**kwargs):
    """Create user for testing"""
    user_model = get_user_model()
    user = user_model.objects.create_user(kwargs)
    return user


@database_sync_to_async
def get_user_token(user):
    """Get user token for testing"""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
    }
