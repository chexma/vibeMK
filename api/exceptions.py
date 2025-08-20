"""
Custom exceptions for CheckMK API
"""

from typing import Optional, Dict, Any


class CheckMKError(Exception):
    """Base exception for CheckMK API errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


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