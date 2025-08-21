"""
Pytest configuration and shared fixtures for vibeMK tests
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from api import CheckMKClient
from config import CheckMKConfig, MCPConfig


@pytest.fixture
def mock_config():
    """Mock CheckMK configuration for testing"""
    return CheckMKConfig(
        server_url="http://test-checkmk.local:8080",
        site="test_site",
        username="test_user",
        password="test_password",
        verify_ssl=False,
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def mock_mcp_config():
    """Mock MCP configuration for testing"""
    return MCPConfig(name="test-vibemk", version="0.1.0")


@pytest.fixture
def mock_checkmk_client(mock_config):
    """Mock CheckMK client with predefined responses"""
    client = CheckMKClient(mock_config)

    # Mock HTTP methods
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()

    return client


@pytest.fixture
def sample_host_data():
    """Sample host data for testing"""
    return {
        "host_name": "test-server-01",
        "folder": "/servers/test",
        "attributes": {"ipaddress": "192.168.1.100", "alias": "Test Server 01", "site": "test_site"},
    }


@pytest.fixture
def sample_service_data():
    """Sample service data for testing"""
    return {
        "host_name": "test-server-01",
        "service_description": "CPU utilization",
        "state": 0,
        "plugin_output": "OK - CPU usage is 25%",
        "performance_data": "cpu=25%;80;90;0;100",
    }


@pytest.fixture
def mock_checkmk_responses():
    """Predefined CheckMK API responses for testing"""
    return {
        "version": {
            "success": True,
            "data": {
                "site": "test_site",
                "group": "checkmk",
                "rest_api": {"revision": "1.0"},
                "versions": {"checkmk": "2.3.0p1"},
                "edition": "cre",
            },
        },
        "hosts": {
            "success": True,
            "data": {
                "value": [
                    {
                        "id": "test-server-01",
                        "extensions": {
                            "folder": "/servers/test",
                            "attributes": {"ipaddress": "192.168.1.100", "alias": "Test Server 01"},
                        },
                    }
                ]
            },
        },
        "host_status": {
            "success": True,
            "data": {
                "extensions": {
                    "name": "test-server-01",
                    "state": 0,
                    "hard_state": 0,
                    "state_type": 1,
                    "plugin_output": "PING OK - Packet loss = 0%, RTA = 1.23ms",
                    "last_check": 1640995200,
                    "has_been_checked": True,
                }
            },
        },
        "service_status": {
            "success": True,
            "data": {
                "extensions": {
                    "description": "CPU utilization",
                    "state": 0,
                    "hard_state": 0,
                    "state_type": 1,
                    "plugin_output": "OK - CPU usage is 25%",
                    "last_check": 1640995200,
                    "has_been_checked": True,
                }
            },
        },
        "error_404": {
            "success": False,
            "data": {"title": "Not Found", "status": 404, "detail": "The requested resource was not found"},
        },
        "error_401": {
            "success": False,
            "data": {"title": "Unauthorized", "status": 401, "detail": "Invalid credentials"},
        },
    }
