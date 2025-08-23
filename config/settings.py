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


@dataclass
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

    @classmethod
    def from_env(cls) -> "CheckMKConfig":
        """Load configuration from environment variables"""
        return cls(
            server_url=os.environ.get("CHECKMK_SERVER_URL", "http://localhost:8080"),
            site=os.environ.get("CHECKMK_SITE", "cmk"),
            username=os.environ.get("CHECKMK_USERNAME", "automation"),
            password=os.environ.get("CHECKMK_PASSWORD", ""),
            verify_ssl=os.environ.get("CHECKMK_VERIFY_SSL", "true").lower() == "true",
            timeout=int(os.environ.get("CHECKMK_TIMEOUT", "30")),
            max_retries=int(os.environ.get("CHECKMK_MAX_RETRIES", "3")),
            debug=os.environ.get("CHECKMK_DEBUG", "false").lower() == "true",
        )

    def validate(self) -> None:
        """Validate configuration"""
        if not self.server_url:
            raise ValueError("CHECKMK_SERVER_URL is required")
        if not self.username:
            raise ValueError("CHECKMK_USERNAME is required")
        if not self.password:
            raise ValueError("CHECKMK_PASSWORD is required")
        if not self.site:
            raise ValueError("CHECKMK_SITE is required")


@dataclass
class MCPConfig:
    """MCP server configuration"""

    protocol_version: str = "2024-11-05"  # Keep stable version for now
    server_name: str = "vibeMK"
    server_version: str = "0.3.9"
