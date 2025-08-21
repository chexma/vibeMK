"""
Integration Tests for vibeMK

These tests require a running CheckMK instance and can be run optionally.
Set INTEGRATION_TESTS=true and provide real CheckMK credentials to run.
"""

import pytest
import os
from unittest.mock import patch
from config import CheckMKConfig
from api import CheckMKClient
from mcp.server import CheckMKMCPServer


# Skip integration tests by default
pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION_TESTS") != "true", reason="Integration tests require INTEGRATION_TESTS=true"
)


@pytest.fixture
def integration_config():
    """Real CheckMK configuration for integration tests"""
    return CheckMKConfig(
        server_url=os.environ.get("CHECKMK_SERVER_URL", "http://localhost:8080"),
        site=os.environ.get("CHECKMK_SITE", "cmk"),
        username=os.environ.get("CHECKMK_USERNAME", "automation"),
        password=os.environ.get("CHECKMK_PASSWORD", ""),
        verify_ssl=os.environ.get("CHECKMK_VERIFY_SSL", "false").lower() == "true",
        timeout=int(os.environ.get("CHECKMK_TIMEOUT", "30")),
        max_retries=int(os.environ.get("CHECKMK_MAX_RETRIES", "3")),
    )


@pytest.fixture
def real_client(integration_config):
    """Real CheckMK client for integration tests"""
    return CheckMKClient(integration_config)


class TestIntegration:
    """Integration tests with real CheckMK instance"""

    @pytest.mark.asyncio
    async def test_real_connection(self, real_client):
        """Test connection to real CheckMK instance"""
        result = await real_client.get("version")

        assert result["success"] is True
        assert "data" in result
        assert "versions" in result["data"]
        assert "checkmk" in result["data"]["versions"]

    @pytest.mark.asyncio
    async def test_real_hosts_list(self, real_client):
        """Test listing real hosts"""
        result = await real_client.get("domain-types/host/collections/all")

        assert result["success"] is True
        assert "data" in result
        assert "value" in result["data"]
        assert isinstance(result["data"]["value"], list)

    @pytest.mark.asyncio
    async def test_real_mcp_server_workflow(self):
        """Test complete MCP server workflow with real CheckMK"""
        # Skip if credentials not provided
        if not all(
            [
                os.environ.get("CHECKMK_SERVER_URL"),
                os.environ.get("CHECKMK_USERNAME"),
                os.environ.get("CHECKMK_PASSWORD"),
            ]
        ):
            pytest.skip("Real CheckMK credentials not provided")

        # Initialize MCP server
        server = CheckMKMCPServer()

        # Test tools list
        tools_request = {"jsonrpc": "2.0", "id": "integration-1", "method": "tools/list"}

        tools_response = await server.handle_request(tools_request)
        assert tools_response["jsonrpc"] == "2.0"
        assert "result" in tools_response
        assert len(tools_response["result"]["tools"]) > 0

        # Test connection tool
        connection_request = {
            "jsonrpc": "2.0",
            "id": "integration-2",
            "method": "tools/call",
            "params": {"name": "vibemk_debug_checkmk_connection", "arguments": {}},
        }

        connection_response = await server.handle_request(connection_request)
        assert "result" in connection_response
        assert len(connection_response["result"]["content"]) > 0

        # Should contain success indicator
        content_text = connection_response["result"]["content"][0]["text"]
        assert "✅" in content_text or "Connection successful" in content_text

    @pytest.mark.asyncio
    async def test_host_operations_workflow(self, real_client):
        """Test complete host operations workflow"""
        # This test should only run if we have a test host available
        test_host = os.environ.get("TEST_HOST_NAME")
        if not test_host:
            pytest.skip("TEST_HOST_NAME not provided for host operations test")

        # Test host status
        host_status = await real_client.get(f"objects/host/{test_host}", params={"columns": ["state", "plugin_output"]})

        if host_status["success"]:
            # Host exists, test status retrieval
            assert "data" in host_status
            assert "extensions" in host_status["data"]
        else:
            # Host doesn't exist, which is also a valid test result
            assert host_status["data"]["status"] == 404

    @pytest.mark.asyncio
    async def test_service_discovery_workflow(self, real_client):
        """Test service discovery workflow if test host available"""
        test_host = os.environ.get("TEST_HOST_NAME")
        if not test_host:
            pytest.skip("TEST_HOST_NAME not provided for service discovery test")

        # Test service discovery
        discovery_result = await real_client.post(f"objects/host/{test_host}/actions/discover_services/invoke")

        # Discovery might succeed or fail depending on host state
        # Both are valid outcomes for this test
        assert "success" in discovery_result
        assert "data" in discovery_result

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_host(self, real_client):
        """Test error handling with invalid host"""
        # Try to get status of non-existent host
        result = await real_client.get("objects/host/definitely-not-existing-host-12345")

        # Should get 404 error
        assert result["success"] is False
        assert result["data"]["status"] == 404

    @pytest.mark.asyncio
    async def test_authentication_validation(self):
        """Test authentication validation"""
        # Create client with invalid credentials
        invalid_config = CheckMKConfig(
            server_url=os.environ.get("CHECKMK_SERVER_URL", "http://localhost:8080"),
            site=os.environ.get("CHECKMK_SITE", "cmk"),
            username="invalid_user",
            password="invalid_password",
        )

        invalid_client = CheckMKClient(invalid_config)

        # Should get authentication error
        from api.exceptions import CheckMKAuthenticationError

        with pytest.raises(CheckMKAuthenticationError):
            await invalid_client.get("version")


class TestLoadTesting:
    """Load testing for vibeMK (optional)"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_load(self, real_client):
        """Test handling multiple concurrent requests"""
        import asyncio

        # Create multiple concurrent version requests
        tasks = []
        for i in range(10):
            task = real_client.get("version")
            tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded (or failed gracefully)
        success_count = 0
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                success_count += 1

        # At least some should succeed (depending on server load)
        assert success_count > 0

    @pytest.mark.asyncio
    async def test_rapid_sequential_requests(self, real_client):
        """Test rapid sequential requests"""
        # Make 20 rapid sequential requests
        success_count = 0
        for i in range(20):
            try:
                result = await real_client.get("version")
                if result.get("success"):
                    success_count += 1
            except Exception:
                # Some failures are acceptable under load
                pass

        # Most should succeed
        assert success_count >= 15  # 75% success rate minimum
