"""
Output schemas for the tools whose results get acted on.

Most tools answer in prose, which is the right shape for something a person
reads once. A few answer with data a model then works with -- a host state it
has to compare, a list of problems it has to count, a metric series it has to
summarise -- and parsing that back out of emoji-marked markdown is both
lossy and avoidable.

Those tools declare an `outputSchema` here and return the matching object as
`structuredContent`. The prose stays alongside it, so a transcript still
reads sensibly.

A schema is only added once its handler actually produces the object: a
declared schema with nothing behind it is worse than none, because the
specification lets a client validate against it.
"""

from typing import Any, Dict

_TIMESTAMP = {"type": ["integer", "null"], "description": "Unix timestamp, or null when CheckMK reported none"}

HOST_STATUS = {
    "type": "object",
    "properties": {
        "host_name": {"type": "string"},
        "state": {"type": "string", "enum": ["UP", "DOWN", "UNREACHABLE"], "description": "Monitoring state"},
        "state_code": {"type": "integer", "description": "0 UP, 1 DOWN, 2 UNREACHABLE"},
        "is_hard_state": {"type": "boolean", "description": "Whether CheckMK considers the state settled"},
        "has_been_checked": {"type": "boolean"},
        "plugin_output": {"type": "string", "description": "What the check itself reported"},
        "last_check": _TIMESTAMP,
        "last_state_change": _TIMESTAMP,
    },
    "required": ["host_name", "state", "state_code"],
}

HOST_LIST = {
    "type": "object",
    "properties": {
        "total": {"type": "integer", "description": "Hosts the site reported"},
        "hosts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string"},
                    "state": {"type": "string", "enum": ["UP", "DOWN", "UNREACHABLE", "UNKNOWN"]},
                },
                "required": ["host_name", "state"],
            },
        },
    },
    "required": ["total", "hosts"],
}

PENDING_CHANGES = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "change_id": {"type": "string"},
                    "user": {"type": "string"},
                    "text": {"type": "string"},
                },
            },
        },
    },
    "required": ["count"],
}

# Tool name -> the schema its handler fills.
OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "vibemk_get_host_status": HOST_STATUS,
    "vibemk_get_checkmk_hosts": HOST_LIST,
    "vibemk_get_pending_changes": PENDING_CHANGES,
}


def output_schema_for(name: str) -> Dict[str, Any] | None:
    """The output schema a tool declares, or None when it answers in prose."""
    return OUTPUT_SCHEMAS.get(name)
