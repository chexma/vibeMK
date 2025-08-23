"""
Base handler for vibeMK operations
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from api import CheckMKClient
from utils import get_logger

# Type aliases to avoid import conflicts with built-in 'types' module
ToolArguments = Dict[str, Any]
ToolResult = List[Dict[str, Any]]

logger: logging.Logger = get_logger(__name__)


class BaseHandler(ABC):
    """Base class for all vibeMK handlers"""

    def __init__(self, client: CheckMKClient) -> None:
        self.client = client
        self.logger = logger

    @abstractmethod
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle tool call and return MCP response content"""
        pass

    def success_response(self, message: str, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create success response"""
        text = f"✅ **{message}**"
        if data:
            text += f"\n\n{self._format_data(data)}"
        return [{"type": "text", "text": text}]

    def error_response(self, message: str, error_details: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create error response"""
        text = f"❌ **{message}**"
        if error_details:
            text += f"\n\n{error_details}"
        return [{"type": "text", "text": text}]

    def info_response(self, message: str, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create info response"""
        text = f"ℹ️ **{message}**"
        if data:
            text += f"\n\n{self._format_data(data)}"
        return [{"type": "text", "text": text}]

    def _format_data(self, data: Union[Dict[str, Any], List[Any], str, int, float, None]) -> str:
        """Format data for display"""
        if isinstance(data, dict):
            formatted_lines: List[str] = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    formatted_lines.append(f"**{key}**: {len(value) if isinstance(value, list) else 'object'}")
                else:
                    formatted_lines.append(f"**{key}**: {value}")
            return "\n".join(formatted_lines)
        return str(data)
