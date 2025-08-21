"""
Base handler for vibeMK operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from api import CheckMKClient
from utils import get_logger

logger = get_logger(__name__)


class BaseHandler(ABC):
    """Base class for all vibeMK handlers"""

    def __init__(self, client: CheckMKClient):
        self.client = client
        self.logger = logger

    @abstractmethod
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle tool call and return MCP response content"""
        pass

    def success_response(self, message: str, data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Create success response"""
        text = f"✅ **{message}**"
        if data:
            text += f"\n\n{self._format_data(data)}"
        return [{"type": "text", "text": text}]

    def error_response(self, message: str, error_details: str = None) -> List[Dict[str, Any]]:
        """Create error response"""
        text = f"❌ **{message}**"
        if error_details:
            text += f"\n\n{error_details}"
        return [{"type": "text", "text": text}]

    def info_response(self, message: str, data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Create info response"""
        text = f"ℹ️ **{message}**"
        if data:
            text += f"\n\n{self._format_data(data)}"
        return [{"type": "text", "text": text}]

    def _format_data(self, data: Dict[str, Any]) -> str:
        """Format data for display"""
        if isinstance(data, dict):
            formatted_lines = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    formatted_lines.append(f"**{key}**: {len(value) if isinstance(value, list) else 'object'}")
                else:
                    formatted_lines.append(f"**{key}**: {value}")
            return "\n".join(formatted_lines)
        return str(data)
