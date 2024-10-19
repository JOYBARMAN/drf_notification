NOTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "model": {"type": "string"},
        "instance": {"type": "object"},
        "method": {
            "type": "string",
            "enum": ["POST", "PATCH", "GET", "DELETE", "UPDATE", "UNDEFINED"],
        },
        "changed_data": {"type": "object"},
    },
    "required": ["message","model", "instance", "method", "changed_data"],
}
