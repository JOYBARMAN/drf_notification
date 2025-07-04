from notifications.utils.consumers import validate_token

from channels.middleware import BaseMiddleware


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        """Middleware to authenticate WebSocket connections using JWT tokens."""
        token = None
        # Get token from subprotocol
        subprotocols = scope.get("subprotocols", [])
        if subprotocols:
            token = subprotocols[0]
            scope["subprotocols"] = token

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
            scope["error"] = "Provide an access token in the subprotocols"

        return await super().__call__(scope, receive, send)
