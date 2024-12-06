def user1_payload():
    return {
        "username": "test_user_1",
        "email": "test1@gmail.com",
        "password": "test_password1",
    }


def user2_payload():
    return {
        "username": "test_user_2",
        "email": "test2@gmail.com",
        "password": "test_password2",
    }


def notification_message_payload(total: int):
    import random

    notification_payload = []

    method = ["POST", "PATCH", "GET", "DELETE", "PUT", "UNDEFINED"]
    for i in range(total):
        notification_payload.append(
            {
                "message": f"This is a test notification {i}",
                "method": random.choice(method),
            }
        )

    return notification_payload
