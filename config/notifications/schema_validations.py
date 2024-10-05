NOTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "instance": {"type": "object"},
        "method": {
            "type": "string",
            "enum": ["POST", "PATCH", "GET", "DELETE", "UPDATE", "UNDEFINED"],
        },
        "changed_data": {"type": "object"},
    },
    "required": ["message", "instance", "method", "changed_data"],
}
