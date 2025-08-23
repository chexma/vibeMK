"""
CheckMK API Client with automatic URL detection and robust error handling

Copyright (C) 2024 Andre <andre@example.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import base64
import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

from api.exceptions import (
    CheckMKAPIError,
    CheckMKAuthenticationError,
    CheckMKConnectionError,
    CheckMKError,
    CheckMKNotFoundError,
    CheckMKPermissionError,
)
from config import CheckMKConfig

# Avoid conflict with built-in 'types' module - comment out for now
# from checkmk_types.checkmk_types import CheckMKAPIResponse

logger = logging.getLogger(__name__)


class CheckMKClient:
    """CheckMK REST API client with automatic URL detection"""

    def __init__(self, config: CheckMKConfig, skip_url_detection: bool = False):
        self.config = config
        self._setup_headers()
        self._ssl_context = self._create_ssl_context()

        if skip_url_detection:
            # For testing - use first pattern without detection
            self.api_base_url = f"{self.config.server_url}/cmk/check_mk/api/1.0"
        else:
            self.api_base_url = self._detect_api_url()

    def _setup_headers(self) -> None:
        """Setup HTTP headers for authentication"""
        credentials = f"{self.config.username}:{self.config.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"vibeMK/{self.config.__class__.__module__}",
        }

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context based on configuration"""
        if not self.config.verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        return None

    def _detect_api_url(self) -> str:
        """Detect correct CheckMK API URL by testing different patterns"""
        debug_results = []

        test_patterns = [
            f"{self.config.server_url}/cmk/check_mk/api/1.0",
            f"{self.config.server_url}/{self.config.site}/check_mk/api/1.0",
            f"{self.config.server_url}/check_mk/api/1.0",
            f"{self.config.server_url}/api/1.0",
            f"{self.config.server_url}/{self.config.site}/cmk/check_mk/api/1.0",
        ]

        for base_url in test_patterns:
            try:
                test_url = f"{base_url}/version"
                debug_results.append(f"Testing: {test_url}")

                req = urllib.request.Request(test_url, headers=self.headers)
                with urllib.request.urlopen(req, context=self._ssl_context, timeout=self.config.timeout) as response:
                    if response.status == 200:
                        debug_results.append(f"SUCCESS: {base_url}")
                        self._debug_results = debug_results
                        logger.info(f"Detected API URL: {base_url}")
                        return base_url
                    else:
                        debug_results.append(f"HTTP {response.status}: {base_url}")

            except urllib.error.HTTPError as e:
                debug_results.append(f"HTTP {e.code} ({e.reason}): {base_url}")
            except Exception as e:
                debug_results.append(f"ERROR ({str(e)}): {base_url}")

        # Store debug results for troubleshooting
        self._debug_results = debug_results
        fallback_url = f"{self.config.server_url}/cmk/check_mk/api/1.0"
        debug_results.append(f"FALLBACK: {fallback_url}")
        logger.warning(f"Using fallback API URL: {fallback_url}")
        return fallback_url

    def get_debug_results(self) -> List[str]:
        """Get URL detection debug results"""
        return getattr(self, "_debug_results", ["No debug info available"])

    def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0,
        use_api_prefix: bool = True,
    ) -> Dict[str, Any]:
        """Make HTTP request to CheckMK API with retry logic"""

        if use_api_prefix:
            url = f"{self.api_base_url}/{endpoint}"
        else:
            # For CheckMK View API and other non-REST endpoints
            url = f"{self.config.server_url}/cmk/{endpoint}"
        if params:
            # Handle CheckMK API specific parameter encoding
            url_params = []
            for key, value in params.items():
                if key == "columns" and isinstance(value, list):
                    # Multiple columns parameters: columns=col1&columns=col2
                    for col in value:
                        url_params.append(f"columns={urllib.parse.quote(str(col))}")
                elif key == "query" and isinstance(value, dict):
                    # JSON query parameter: query={"op": "=", ...}
                    query_json = json.dumps(value)
                    url_params.append(f"query={urllib.parse.quote(query_json)}")
                else:
                    # Standard parameter encoding
                    url_params.append(f"{key}={urllib.parse.quote(str(value))}")

            if url_params:
                url += "?" + "&".join(url_params)

        try:
            # Merge default headers with custom headers
            request_headers = self.headers.copy()
            if custom_headers:
                request_headers.update(custom_headers)

            req = urllib.request.Request(url, headers=request_headers)
            req.get_method = lambda: method

            if method in ["POST", "PUT", "PATCH"] and data:
                req.data = json.dumps(data).encode()

            logger.debug(f"{method} {url}")

            with urllib.request.urlopen(req, context=self._ssl_context, timeout=self.config.timeout) as response:
                response_data = response.read().decode()

                try:
                    parsed_data = json.loads(response_data) if response_data else {}
                except json.JSONDecodeError as e:
                    raise CheckMKAPIError(f"Invalid JSON response: {str(e)}", response.status, {"raw": response_data})

                result = {
                    "status": response.status,
                    "data": parsed_data,
                    "success": True,
                    "raw_content": response_data,  # Keep raw content for view API parsing
                    "headers": dict(response.headers),  # Include response headers for ETag support
                }

                logger.debug(f"Response: {response.status}")
                return result

        except urllib.error.HTTPError as e:
            return self._handle_http_error(
                e, endpoint, method, data, params, custom_headers, retry_count, use_api_prefix
            )
        except (CheckMKAPIError, CheckMKConnectionError, CheckMKError):
            # Don't catch and re-wrap our own exceptions
            raise
        except Exception as e:
            return self._handle_general_error(
                e, endpoint, method, data, params, custom_headers, retry_count, use_api_prefix
            )

    def _handle_http_error(
        self,
        error: urllib.error.HTTPError,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        custom_headers: Optional[Dict[str, str]],
        retry_count: int,
        use_api_prefix: bool = True,
    ) -> Dict[str, Any]:
        """Handle HTTP errors with appropriate exceptions and retries"""

        try:
            error_data = json.loads(error.read().decode())
        except:
            error_data = {"error": error.reason}

        # Retry logic for transient errors (500, 502, 503, 504)
        if error.code in [500, 502, 503, 504] and retry_count < self.config.max_retries:
            time.sleep(2**retry_count)  # Exponential backoff
            return self.request(endpoint, method, data, params, custom_headers, retry_count + 1, use_api_prefix)

        # Map HTTP status codes to custom exceptions
        if error.code == 401:
            raise CheckMKAuthenticationError(f"Authentication failed: {error.reason}", error.code, error_data)
        elif error.code == 403:
            raise CheckMKPermissionError(f"Permission denied: {error.reason}", error.code, error_data)
        elif error.code == 404:
            raise CheckMKNotFoundError(f"Resource not found: {error.reason}", error.code, error_data)
        else:
            raise CheckMKAPIError(f"HTTP {error.code}: {error.reason}", error.code, error_data)

    def _handle_general_error(
        self,
        error: Exception,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        custom_headers: Optional[Dict[str, str]],
        retry_count: int,
        use_api_prefix: bool = True,
    ) -> Dict[str, Any]:
        """Handle general connection errors"""

        # Handle timeout errors specifically - don't retry timeouts
        if isinstance(error, (TimeoutError, OSError)) and "timeout" in str(error).lower():
            raise CheckMKConnectionError(f"Request timeout: {str(error)}")

        # Handle TimeoutError specifically (might not contain "timeout" in message)
        if isinstance(error, TimeoutError):
            raise CheckMKConnectionError(f"Request timeout: {str(error)}")

        # Handle URL errors (connection refused, DNS issues, etc.)
        if isinstance(error, urllib.error.URLError):
            raise CheckMKConnectionError(f"Connection error: {str(error)}")

        # Retry logic for general connection errors
        if retry_count < self.config.max_retries and not isinstance(error, StopIteration):
            time.sleep(2**retry_count)
            return self.request(endpoint, method, data, params, custom_headers, retry_count + 1, use_api_prefix)

        # Don't retry StopIteration errors (from test mocks)
        if isinstance(error, StopIteration):
            raise CheckMKConnectionError("Mock iteration exhausted")

        raise CheckMKConnectionError(f"Connection failed: {str(error)}")

    # Convenience methods
    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, use_api_prefix: bool = True
    ) -> Dict[str, Any]:
        """GET request with optional non-API endpoints"""
        return self.request(endpoint, "GET", params=params, use_api_prefix=use_api_prefix)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request"""
        return self.request(endpoint, "POST", data=data)

    def put(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """PUT request with optional custom headers"""
        return self.request(endpoint, "PUT", data=data, custom_headers=headers)

    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """DELETE request with optional parameters"""
        return self.request(endpoint, "DELETE", params=params)

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """PATCH request"""
        return self.request(endpoint, "PATCH", data=data)
