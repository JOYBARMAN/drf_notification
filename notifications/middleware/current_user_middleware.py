from rest_framework_simplejwt.authentication import JWTAuthentication

from notifications.utils import set_current_user


class DRFCurrentUserMiddleware:
    """Middleware to set the current user after JWT authentication"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Authenticate the user with JWT
        jwt_authenticator = JWTAuthentication()
        try:
            # Get the user from the JWT token
            user, _ = jwt_authenticator.authenticate(request)
        except Exception:
            user = None

        # Set the current user
        set_current_user(user)

        response = self.get_response(request)
        return response
