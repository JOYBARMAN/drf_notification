from notifications.utils import validate_token, get_token_from_scope

from channels.middleware import BaseMiddleware


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):

        token = get_token_from_scope(scope)

        if token:
            # Validate the token
            user_id = validate_token(token)

            if user_id:
                scope["user_id"] = user_id
            else:
                scope["error"] = "Token is invalid or expired"

        else:
            scope["error"] = "Provide an access token in the headers."

        return await super().__call__(scope, receive, send)
