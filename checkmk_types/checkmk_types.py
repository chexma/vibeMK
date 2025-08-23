"""
CheckMK-specific type definitions for enhanced type safety
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

# State definitions
HostState = Literal[0, 1, 2]  # UP, DOWN, UNREACHABLE
ServiceState = Literal[0, 1, 2, 3]  # OK, WARNING, CRITICAL, UNKNOWN
StateType = Literal[0, 1]  # SOFT, HARD


# Host-related types
class HostAttributes(TypedDict, total=False):
    ipaddress: str
    alias: str
    site: str
    tag_agent: str
    tag_snmp_ds: str
    parents: List[str]
    additional_ipv4addresses: List[str]
    additional_ipv6addresses: List[str]


class HostStatus(TypedDict):
    name: str
    state: HostState
    hard_state: HostState
    state_type: StateType
    plugin_output: str
    last_check: Optional[int]
    last_state_change: Optional[int]
    has_been_checked: bool


class HostData(TypedDict):
    host_name: str
    folder: str
    attributes: HostAttributes


# Service-related types
class ServiceStatus(TypedDict):
    description: str
    state: ServiceState
    hard_state: ServiceState
    state_type: StateType
    plugin_output: str
    last_check: Optional[int]
    last_state_change: Optional[int]
    has_been_checked: bool


class ServiceData(TypedDict):
    host_name: str
    service_description: str
    state: ServiceState
    plugin_output: str
    performance_data: Optional[str]


# Downtime-related types
DowntimeType = Literal["host", "service"]


class DowntimeData(TypedDict):
    downtime_type: DowntimeType
    host_name: str
    start_time: str  # ISO format
    end_time: str  # ISO format
    comment: str
    service_descriptions: Optional[List[str]]


class DowntimeResponse(TypedDict):
    id: str
    extensions: Dict[str, Any]


# Acknowledgement-related types
class AcknowledgementData(TypedDict):
    host_name: str
    comment: str
    sticky: bool
    persistent: bool
    notify: bool
    service_description: Optional[str]


# Metrics-related types
class TimeRange(TypedDict):
    start: str  # Datetime string format
    end: str  # Datetime string format


class MetricRequest(TypedDict):
    time_range: TimeRange
    reduce: Literal["max", "min", "avg", "sum"]
    site: str
    host_name: str
    service_description: str
    type: Literal["single_metric"]
    metric_id: str


class MetricData(TypedDict):
    title: str
    color: str
    line_type: str
    data: List[Optional[float]]


class MetricResponse(TypedDict):
    metrics: Dict[str, MetricData]
    time_range: List[int]
    step: int


# Rule-related types
class RuleConditions(TypedDict, total=False):
    host_name: List[str]
    host_tags: List[str]
    service_description: List[str]


class RuleProperties(TypedDict, total=False):
    disabled: bool
    comment: str
    description: str


class RuleData(TypedDict):
    properties: RuleProperties
    value_raw: str  # Python string literal
    conditions: RuleConditions
    ruleset: str
    folder: str


# Folder-related types
class FolderAttributes(TypedDict, total=False):
    tag_agent: str
    tag_snmp_ds: str
    meta_data: Dict[str, Any]


class FolderData(TypedDict):
    name: str
    parent: str  # Use "~" for root
    attributes: FolderAttributes


# User-related types
class UserAttributes(TypedDict, total=False):
    alias: str
    email: str
    pager: str
    roles: List[str]
    contactgroups: List[str]
    disable_notifications: bool


class UserData(TypedDict):
    username: str
    fullname: str
    attributes: UserAttributes


# Group-related types
class ContactGroupData(TypedDict):
    name: str
    alias: str


class HostGroupData(TypedDict):
    name: str
    alias: str


# Time period-related types
class TimeRangeSpec(TypedDict):
    start: str  # Format: "HH:MM"
    end: str  # Format: "HH:MM"


class DayTimeRange(TypedDict):
    day: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    time_ranges: List[TimeRangeSpec]


class TimePeriodData(TypedDict):
    name: str
    alias: str
    active_time_ranges: List[DayTimeRange]


# API Response types
class CheckMKSuccessResponse(TypedDict):
    success: Literal[True]
    data: Dict[str, Any]


class CheckMKErrorResponse(TypedDict):
    success: Literal[False]
    data: Dict[str, Any]


CheckMKAPIResponse = Union[CheckMKSuccessResponse, CheckMKErrorResponse]


# Collection response types
class CollectionResponse(TypedDict):
    value: List[Dict[str, Any]]


class ObjectResponse(TypedDict):
    extensions: Dict[str, Any]
