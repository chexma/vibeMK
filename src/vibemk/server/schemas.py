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
        "state": {
            "type": "string",
            "enum": ["UP", "DOWN", "UNREACHABLE", "UNKNOWN"],
            "description": "Monitoring state; UNKNOWN when CheckMK reported none",
        },
        "state_code": {"type": "integer", "description": "0 UP, 1 DOWN, 2 UNREACHABLE, -1 unavailable"},
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

SERVICE_STATUS = {
    "type": "object",
    "properties": {
        "host_name": {"type": "string"},
        "service_description": {"type": "string"},
        "state": {
            "type": "string",
            "enum": ["OK", "WARNING", "CRITICAL", "UNKNOWN", "UNAVAILABLE"],
            "description": "Monitoring state; UNAVAILABLE when CheckMK reported none (UNKNOWN is a real state)",
        },
        "state_code": {"type": ["integer", "null"], "description": "0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN"},
        "is_hard_state": {"type": "boolean", "description": "Whether CheckMK considers the state settled"},
        "plugin_output": {"type": "string", "description": "What the check itself reported"},
        "last_check": _TIMESTAMP,
        "last_state_change": _TIMESTAMP,
    },
    "required": ["host_name", "service_description", "state", "state_code"],
}

_HANDLING = {
    "acknowledged": {"type": "boolean", "description": "Someone has acknowledged the problem"},
    "in_downtime": {"type": "boolean", "description": "The object is inside a scheduled downtime"},
}

CURRENT_PROBLEMS = {
    "type": "object",
    "properties": {
        "total": {"type": "integer"},
        "host_problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string"},
                    "state": {"type": "string", "description": "DOWN or UNREACHABLE"},
                    "state_code": {"type": "integer"},
                    **_HANDLING,
                },
                "required": ["host_name", "state", "state_code"],
            },
        },
        "service_problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string"},
                    "service_description": {"type": "string"},
                    "state": {"type": "string", "description": "WARNING, CRITICAL or UNKNOWN"},
                    "state_code": {"type": "integer"},
                    "plugin_output": {"type": "string"},
                    "last_state_change": _TIMESTAMP,
                    **_HANDLING,
                },
                "required": ["host_name", "service_description", "state", "state_code"],
            },
        },
    },
    "required": ["total", "host_problems", "service_problems"],
}

DOWNTIME_LIST = {
    "type": "object",
    "properties": {
        "total": {"type": "integer"},
        "downtimes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "downtime_id": {"type": "string", "description": "What vibemk_delete_downtime takes"},
                    "host_name": {"type": "string"},
                    "service_description": {"type": ["string", "null"], "description": "null for a host downtime"},
                    "is_service": {"type": "boolean"},
                    "start_time": {"type": "string", "description": "ISO 8601, as CheckMK reports it"},
                    "end_time": {"type": "string", "description": "ISO 8601, as CheckMK reports it"},
                    "active": {"type": "boolean", "description": "In effect now, rather than scheduled ahead"},
                    "comment": {"type": "string"},
                    "author": {"type": "string"},
                    "recurring": {"type": "boolean"},
                },
                "required": ["downtime_id", "host_name", "is_service", "start_time", "end_time", "active"],
            },
        },
    },
    "required": ["total", "downtimes"],
}

_NUMBER = {"type": ["number", "null"]}

METRIC_DATA = {
    "type": "object",
    "description": "Without a metric_name, the metrics there are; with one, its values over the window",
    "properties": {
        "host_name": {"type": "string"},
        "service_description": {"type": ["string", "null"], "description": "null for a host metric"},
        "metric_id": {"type": ["string", "null"], "description": "null when listing what is available"},
        "available_metrics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Present when listing: the IDs metric_name accepts",
        },
        "time_range": {"type": "string"},
        "start": {"type": ["string", "null"], "description": "Window CheckMK actually used, ISO 8601"},
        "end": {"type": ["string", "null"]},
        "step": {"type": ["integer", "null"], "description": "Seconds per data point"},
        "series": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "points": {"type": "integer", "description": "Data points in the window, empty ones included"},
                    "latest": {**_NUMBER, "description": "Last point that carries a value"},
                    "min": _NUMBER,
                    "max": _NUMBER,
                    "avg": _NUMBER,
                },
                "required": ["title", "points", "latest", "min", "max", "avg"],
            },
        },
    },
    "required": ["host_name", "series"],
}

AVAILABLE_METRICS = {
    "type": "object",
    "properties": {
        "host_name": {"type": "string"},
        "service_description": {"type": ["string", "null"]},
        "metric_id": {"type": "null"},
        "available_metrics": {"type": "array", "items": {"type": "string"}},
        "series": {"type": "array", "maxItems": 0},
    },
    "required": ["host_name", "available_metrics"],
}

# Tool name -> the schema its handler fills.
OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "vibemk_get_host_status": HOST_STATUS,
    "vibemk_get_checkmk_hosts": HOST_LIST,
    "vibemk_get_pending_changes": PENDING_CHANGES,
    "vibemk_get_service_status": SERVICE_STATUS,
    "vibemk_get_current_problems": CURRENT_PROBLEMS,
    "vibemk_get_downtimes": DOWNTIME_LIST,
    "vibemk_list_downtimes": DOWNTIME_LIST,
    "vibemk_get_active_downtimes": DOWNTIME_LIST,
    "vibemk_get_service_metrics": METRIC_DATA,
    "vibemk_get_host_metrics": METRIC_DATA,
    "vibemk_list_available_metrics": AVAILABLE_METRICS,
}


def output_schema_for(name: str) -> Dict[str, Any] | None:
    """The output schema a tool declares, or None when it answers in prose."""
    return OUTPUT_SCHEMAS.get(name)
