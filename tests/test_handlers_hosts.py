"""
Tests for Host Handler
"""

import pytest
from unittest.mock import AsyncMock, patch
from handlers.hosts import HostHandler
from api.exceptions import CheckMKAPIError


class TestHostHandler:
    """Test Host Handler functionality"""

    @pytest.fixture
    def host_handler(self, mock_checkmk_client):
        """Create host handler with mocked client"""
        return HostHandler(mock_checkmk_client)

    @pytest.mark.asyncio
    async def test_get_checkmk_hosts_success(self, host_handler, mock_checkmk_responses):
        """Test successful hosts retrieval"""
        # Setup mock
        host_handler.client.get.return_value = mock_checkmk_responses["hosts"]
        
        # Execute
        result = await host_handler.handle("vibemk_get_checkmk_hosts", {})
        
        # Verify
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "test-server-01" in result[0]["text"]
        assert "✅" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_get_checkmk_hosts_with_filter(self, host_handler, mock_checkmk_responses):
        """Test hosts retrieval with name filter"""
        # Setup mock
        host_handler.client.get.return_value = mock_checkmk_responses["hosts"]
        
        # Execute with filter
        result = await host_handler.handle("vibemk_get_checkmk_hosts", {
            "host_name_filter": "test-server"
        })
        
        # Verify
        assert len(result) == 1
        assert "test-server-01" in result[0]["text"]
        host_handler.client.get.assert_called_with(
            "domain-types/host/collections/all",
            params={"host_name": "~test-server"}
        )

    @pytest.mark.asyncio
    async def test_get_host_status_success(self, host_handler, mock_checkmk_responses):
        """Test successful host status retrieval"""
        # Setup mock
        host_handler.client.get.return_value = mock_checkmk_responses["host_status"]
        
        # Execute
        result = await host_handler.handle("vibemk_get_host_status", {
            "host_name": "test-server-01"
        })
        
        # Verify
        assert len(result) == 1
        assert "🟢 **UP**" in result[0]["text"]
        assert "test-server-01" in result[0]["text"]
        assert "Hard State: 0" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_get_host_status_down(self, host_handler):
        """Test host status when host is DOWN"""
        # Setup mock for DOWN host
        down_response = {
            "success": True,
            "data": {
                "extensions": {
                    "name": "test-server-01",
                    "state": 1,
                    "hard_state": 1,
                    "state_type": 1,
                    "plugin_output": "CRITICAL - Host unreachable",
                    "last_check": 1640995200,
                    "has_been_checked": True
                }
            }
        }
        host_handler.client.get.return_value = down_response
        
        # Execute
        result = await host_handler.handle("vibemk_get_host_status", {
            "host_name": "test-server-01"
        })
        
        # Verify
        assert "🔴 **DOWN**" in result[0]["text"]
        assert "Hard State: 1" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_create_host_success(self, host_handler):
        """Test successful host creation"""
        # Setup mock
        create_response = {
            "success": True,
            "data": {"id": "new-test-server"}
        }
        host_handler.client.post.return_value = create_response
        
        # Execute
        result = await host_handler.handle("vibemk_create_host", {
            "host_name": "new-test-server",
            "folder": "/servers",
            "attributes": {
                "ipaddress": "192.168.1.101",
                "alias": "New Test Server"
            }
        })
        
        # Verify
        assert len(result) == 1
        assert "✅" in result[0]["text"]
        assert "new-test-server" in result[0]["text"]
        
        # Verify API call
        host_handler.client.post.assert_called_once()
        call_args = host_handler.client.post.call_args
        assert call_args[0][0] == "domain-types/host/collections/all"
        assert "new-test-server" in str(call_args[1]["data"])

    @pytest.mark.asyncio
    async def test_create_host_missing_parameters(self, host_handler):
        """Test host creation with missing required parameters"""
        # Execute without required parameters
        result = await host_handler.handle("vibemk_create_host", {
            "host_name": "new-server"
            # Missing folder and attributes
        })
        
        # Verify error response
        assert len(result) == 1
        assert "❌" in result[0]["text"]
        assert "required" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_delete_host_success(self, host_handler):
        """Test successful host deletion"""
        # Setup mock
        delete_response = {"success": True, "data": {}}
        host_handler.client.delete.return_value = delete_response
        
        # Execute
        result = await host_handler.handle("vibemk_delete_host", {
            "host_name": "test-server-01"
        })
        
        # Verify
        assert len(result) == 1
        assert "✅" in result[0]["text"]
        assert "deleted" in result[0]["text"].lower()
        
        # Verify API call
        host_handler.client.delete.assert_called_with("objects/host/test-server-01")

    @pytest.mark.asyncio
    async def test_move_host_success(self, host_handler):
        """Test successful host move operation"""
        # Setup mock
        move_response = {"success": True, "data": {}}
        host_handler.client.post.return_value = move_response
        
        # Execute
        result = await host_handler.handle("vibemk_move_host", {
            "host_name": "test-server-01",
            "target_folder": "/production/servers"
        })
        
        # Verify
        assert len(result) == 1
        assert "✅" in result[0]["text"]
        assert "moved" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, host_handler):
        """Test API error handling"""
        # Setup mock to raise API error
        host_handler.client.get.side_effect = CheckMKAPIError("API Error", 500)
        
        # Execute
        result = await host_handler.handle("vibemk_get_host_status", {
            "host_name": "test-server-01"
        })
        
        # Verify error handling
        assert len(result) == 1
        assert "❌" in result[0]["text"]
        assert "API Error" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_host_not_found(self, host_handler, mock_checkmk_responses):
        """Test handling when host is not found"""
        # Setup mock for 404 response
        host_handler.client.get.return_value = mock_checkmk_responses["error_404"]
        
        # Execute
        result = await host_handler.handle("vibemk_get_host_status", {
            "host_name": "nonexistent-host"
        })
        
        # Verify
        assert len(result) == 1
        assert "❌" in result[0]["text"]
        assert "not found" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self, host_handler):
        """Test handling of invalid tool names"""
        # Execute with invalid tool name
        result = await host_handler.handle("invalid_tool_name", {})
        
        # Verify error response
        assert len(result) == 1
        assert "❌" in result[0]["text"]
        assert "Unknown tool" in result[0]["text"]