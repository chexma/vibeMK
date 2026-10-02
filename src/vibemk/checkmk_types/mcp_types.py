"""
MCP (Model Context Protocol) specific type definitions
"""

from typing import Any, Dict, List, Literal, TypedDict, Union


# MCP Response types
class MCPTextResponse(TypedDict):
    type: Literal["text"]
    text: str


class MCPResourceResponse(TypedDict):
    type: Literal["resource"]
    resource: Dict[str, Any]


class MCPErrorResponse(TypedDict):
    type: Literal["error"]
    error: str
    details: Dict[str, Any]


MCPResponse = Union[MCPTextResponse, MCPResourceResponse, MCPErrorResponse]

# Tool-related types
ToolArguments = Dict[str, Any]
ToolResult = List[MCPResponse]


# Handler types
class HandlerResponse(TypedDict):
    success: bool
    data: Any
    error: str


# Request types
class ToolCallRequest(TypedDict):
    tool_name: str
    arguments: ToolArguments


# MCP Server types
class MCPServerConfig(TypedDict):
    name: str
    version: str
    tools: List[Dict[str, Any]]
