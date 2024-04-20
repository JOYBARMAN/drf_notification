NOTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "object": {"type": "object"},
    },
    "required": ["message", "object"],
}
