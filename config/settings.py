"""
Configuration management for vibeMK

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

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(repr=False)
class CheckMKConfig:
    """CheckMK server configuration"""

    server_url: str
    site: str
    username: str
    password: str
    verify_ssl: bool = True
    timeout: int = 30
    max_retries: int = 3
    debug: bool = False

    def __post_init__(self):
        """Post-initialization validation and normalization"""
        # Validate required fields
        if not self.server_url:
            raise ValueError("CHECKMK_SERVER_URL is required")
        if not self.username:
            raise ValueError("CHECKMK_USERNAME is required")
        if not self.password:
            raise ValueError("CHECKMK_PASSWORD is required")
        if not self.site:
            raise ValueError("CHECKMK_SITE is required")

        # Validate numeric fields
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        # Normalize URL
        self.server_url = self._normalize_url(self.server_url)

    def _normalize_url(self, url: str) -> str:
        """Normalize server URL"""
        if not url:
            return url

        # Add http:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"

        # Remove trailing slash for consistency
        if url.endswith("/") and len(url) > 1:
            url = url.rstrip("/")

        return url

    def __repr__(self) -> str:
        """String representation with masked password"""
        return (
            f"CheckMKConfig("
            f"server_url='{self.server_url}', "
            f"site='{self.site}', "
            f"username='{self.username}', "
            f"password='***', "
            f"verify_ssl={self.verify_ssl}, "
            f"timeout={self.timeout}, "
            f"max_retries={self.max_retries}, "
            f"debug={self.debug})"
        )

    @classmethod
    def from_env(cls) -> "CheckMKConfig":
        """Load configuration from environment variables"""
        # Handle required fields
        server_url = os.environ.get("CHECKMK_SERVER_URL")
        if not server_url:
            raise ValueError("CHECKMK_SERVER_URL is required")

        site = os.environ.get("CHECKMK_SITE")
        if not site:
            raise ValueError("CHECKMK_SITE is required")

        username = os.environ.get("CHECKMK_USERNAME")
        if not username:
            raise ValueError("CHECKMK_USERNAME is required")

        password = os.environ.get("CHECKMK_PASSWORD")
        if not password:
            raise ValueError("CHECKMK_PASSWORD is required")

        # Handle boolean with fallback
        def safe_bool(value: str, default: bool) -> bool:
            if not value:
                return default
            # Invalid values should return default, not False
            lower_value = value.lower()
            if lower_value in ("true", "1", "yes", "on"):
                return True
            elif lower_value in ("false", "0", "no", "off"):
                return False
            else:
                return default  # Return default for invalid values

        # Handle integer with fallback
        def safe_int(value: str, default: int) -> int:
            if not value:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        return cls(
            server_url=server_url,
            site=site,
            username=username,
            password=password,
            verify_ssl=safe_bool(os.environ.get("CHECKMK_VERIFY_SSL"), True),  # Default to True for security
            timeout=safe_int(os.environ.get("CHECKMK_TIMEOUT"), 30),
            max_retries=safe_int(os.environ.get("CHECKMK_MAX_RETRIES"), 3),
            debug=safe_bool(os.environ.get("CHECKMK_DEBUG"), False),
        )

    def validate(self) -> None:
        """Validate configuration (called automatically in __post_init__)"""
        pass  # Validation now happens in __post_init__


@dataclass
class MCPConfig:
    """MCP server configuration"""

    name: str = "vibemk"
    version: str = "0.3.9"
    protocol_version: str = "2024-11-05"  # Keep stable version for now

    def __post_init__(self):
        """Post-initialization validation"""
        if not self.name or self.name.strip() == "":
            raise ValueError("name cannot be empty")
        if not self.version or self.version.strip() == "":
            raise ValueError("version cannot be empty")

    @property
    def server_name(self) -> str:
        """Alias for name for backward compatibility"""
        return self.name

    @property
    def server_version(self) -> str:
        """Alias for version for backward compatibility"""
        return self.version
