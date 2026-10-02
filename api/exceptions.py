"""
Custom exceptions for CheckMK API
"""

from typing import Any, Dict, Optional


class CheckMKError(Exception):
    """Base exception for CheckMK API errors"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}

    def __str__(self) -> str:
        """Render the message together with CheckMK's own explanation.

        The client parses the error body into response_data, but every handler
        renders an exception with str(e). Without this the caller saw
        "HTTP 400: Bad Request" while CheckMK had said which field was wrong --
        leaving a model nothing to act on but a retry.
        """
        message = super().__str__()

        detail = self.response_data.get("detail") or self.response_data.get("title")
        if not isinstance(detail, str) or not detail.strip():
            return message
        if detail in message:
            return message
        return f"{message} — {detail}"


class CheckMKConnectionError(CheckMKError):
    """Connection-related errors"""

    pass


class CheckMKAuthenticationError(CheckMKError):
    """Authentication errors"""

    pass


class CheckMKPermissionError(CheckMKError):
    """Permission/authorization errors"""

    pass


class CheckMKValidationError(CheckMKError):
    """Input validation errors"""

    pass


class CheckMKNotFoundError(CheckMKError):
    """Resource not found errors"""

    pass


class CheckMKAPIError(CheckMKError):
    """General API errors"""

    pass
