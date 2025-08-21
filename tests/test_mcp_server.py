"""
Tests for MCP Server Implementation
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from mcp.server import CheckMKMCPServer


class TestMCPServer:
    """Test MCP Server functionality"""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance"""
        with patch.dict('os.environ', {
            'CHECKMK_SERVER_URL': 'http://test.local:8080',
            'CHECKMK_SITE': 'test',
            'CHECKMK_USERNAME': 'test_user',
            'CHECKMK_PASSWORD': 'test_pass'
        }):
            return CheckMKMCPServer()

    @pytest.mark.asyncio
    async def test_tools_list_request(self, mcp_server):
        """Test tools/list MCP request"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/list"
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "result" in response
        assert "tools" in response["result"]
        
        # Verify tools have vibemk_ prefix
        tools = response["result"]["tools"]
        assert len(tools) > 0
        for tool in tools:
            assert tool["name"].startswith("vibemk_")
            assert "description" in tool
            assert "inputSchema" in tool

    @pytest.mark.asyncio
    async def test_tool_call_success(self, mcp_server):
        """Test successful tool call"""
        # Mock the connection handler
        with patch.object(mcp_server.connection_handler, 'handle') as mock_handle:
            mock_handle.return_value = [{"type": "text", "text": "✅ Connection successful"}]
            
            request = {
                "jsonrpc": "2.0",
                "id": "test-2",
                "method": "tools/call",
                "params": {
                    "name": "vibemk_debug_checkmk_connection",
                    "arguments": {}
                }
            }
            
            response = await mcp_server.handle_request(request)
            
            # Verify response
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "test-2"
            assert "result" in response
            assert "content" in response["result"]
            assert len(response["result"]["content"]) == 1
            assert "✅" in response["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_tool_call_invalid_tool(self, mcp_server):
        """Test tool call with invalid tool name"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "tools/call",
            "params": {
                "name": "invalid_tool_name",
                "arguments": {}
            }
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-3"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found

    @pytest.mark.asyncio
    async def test_invalid_jsonrpc_method(self, mcp_server):
        """Test invalid JSON-RPC method"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "invalid/method"
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify error response
        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_malformed_request(self, mcp_server):
        """Test malformed JSON-RPC request"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-5"
            # Missing method
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify error response
        assert "error" in response
        assert response["error"]["code"] == -32600  # Invalid request

    @pytest.mark.asyncio
    async def test_tool_call_with_arguments(self, mcp_server):
        """Test tool call with arguments"""
        # Mock the host handler
        with patch.object(mcp_server.host_handler, 'handle') as mock_handle:
            mock_handle.return_value = [{"type": "text", "text": "✅ Host status retrieved"}]
            
            request = {
                "jsonrpc": "2.0",
                "id": "test-6",
                "method": "tools/call",
                "params": {
                    "name": "vibemk_get_host_status",
                    "arguments": {
                        "host_name": "test-server-01"
                    }
                }
            }
            
            response = await mcp_server.handle_request(request)
            
            # Verify response
            assert "result" in response
            mock_handle.assert_called_once_with("vibemk_get_host_status", {
                "host_name": "test-server-01"
            })

    @pytest.mark.asyncio
    async def test_handler_exception(self, mcp_server):
        """Test handler exception handling"""
        # Mock handler to raise exception
        with patch.object(mcp_server.connection_handler, 'handle') as mock_handle:
            mock_handle.side_effect = Exception("Handler error")
            
            request = {
                "jsonrpc": "2.0",
                "id": "test-7",
                "method": "tools/call",
                "params": {
                    "name": "vibemk_debug_checkmk_connection",
                    "arguments": {}
                }
            }
            
            response = await mcp_server.handle_request(request)
            
            # Verify error response
            assert "error" in response
            assert "Handler error" in response["error"]["message"]

    def test_server_initialization(self):
        """Test server initialization with environment variables"""
        with patch.dict('os.environ', {
            'CHECKMK_SERVER_URL': 'http://test.local:8080',
            'CHECKMK_SITE': 'test_site',
            'CHECKMK_USERNAME': 'test_user',
            'CHECKMK_PASSWORD': 'test_password'
        }):
            server = CheckMKMCPServer()
            
            # Verify configuration
            assert server.config.server_url == 'http://test.local:8080'
            assert server.config.site == 'test_site'
            assert server.config.username == 'test_user'
            assert server.config.password == 'test_password'
            
            # Verify handlers are initialized
            assert server.connection_handler is not None
            assert server.host_handler is not None
            assert server.service_handler is not None
            assert server.monitoring_handler is not None
            assert server.configuration_handler is not None

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mcp_server):
        """Test handling concurrent requests"""
        import asyncio
        
        # Mock handlers
        with patch.object(mcp_server.connection_handler, 'handle') as mock_handle:
            mock_handle.return_value = [{"type": "text", "text": "✅ Success"}]
            
            # Create multiple concurrent requests
            requests = []
            for i in range(5):
                request = {
                    "jsonrpc": "2.0",
                    "id": f"test-{i}",
                    "method": "tools/call",
                    "params": {
                        "name": "vibemk_debug_checkmk_connection",
                        "arguments": {}
                    }
                }
                requests.append(mcp_server.handle_request(request))
            
            # Execute concurrently
            responses = await asyncio.gather(*requests)
            
            # Verify all responses
            assert len(responses) == 5
            for i, response in enumerate(responses):
                assert response["id"] == f"test-{i}"
                assert "result" in response