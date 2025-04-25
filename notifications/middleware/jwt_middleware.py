from notifications.utils import validate_token, get_token_from_scope

from channels.middleware import BaseMiddleware


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        # Get the token from the scope headers
        token = get_token_from_scope(scope)

        if token:
            # Validate the token
            user_id = validate_token(token)

            # If the token is valid, set the user_id in the scope
            if user_id:
                scope["user_id"] = user_id
            else:
                # If the token is invalid or expired, set an error message
                scope["error"] = "Token is invalid or expired"

        else:
            # If no token is provided in the headers, set an error message
            scope["error"] = "Provide an access token in the headers."

        return await super().__call__(scope, receive, send)
