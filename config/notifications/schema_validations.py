NOTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "object": {"type": "object"},
        "method": {
            "type": "string",
            "enum": ["POST", "PATCH", "GET", "DELETE", "UPDATE", "UNDEFINED"],
        },
    },
    "required": ["message", "object", "method"],
}
