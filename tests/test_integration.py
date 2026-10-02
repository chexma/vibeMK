"""
Integration Tests for vibeMK

These tests require a running CheckMK instance and can be run optionally.
Set INTEGRATION_TESTS=true and provide real CheckMK credentials to run.

The client is synchronous: it blocks in urllib and returns a dict, and a
failed request raises one of the exceptions in api.exceptions rather than
returning success=False.
"""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from mcp import Client

from api import CheckMKClient
from api.exceptions import CheckMKAuthenticationError, CheckMKNotFoundError
from config import CheckMKConfig
from vibemk_mcp.server import CheckMKMCPServer

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

    def test_real_connection(self, real_client):
        """Test connection to real CheckMK instance"""
        result = real_client.get("version")

        assert result["success"] is True
        assert "data" in result
        assert "versions" in result["data"]
        assert "checkmk" in result["data"]["versions"]

    def test_real_hosts_list(self, real_client):
        """Test listing real hosts"""
        result = real_client.get("domain-types/host/collections/all")

        assert result["success"] is True
        assert "data" in result
        assert "value" in result["data"]
        assert isinstance(result["data"]["value"], list)

    @pytest.mark.asyncio
    async def test_real_mcp_server_workflow(self):
        """Test complete MCP server workflow with real CheckMK, over the protocol"""
        # The server reads its configuration from the environment
        if not all(
            [
                os.environ.get("CHECKMK_SERVER_URL"),
                os.environ.get("CHECKMK_USERNAME"),
                os.environ.get("CHECKMK_PASSWORD"),
            ]
        ):
            pytest.skip("Real CheckMK credentials not provided")

        server = CheckMKMCPServer()

        # The legacy mode runs the initialize handshake and JSON-RPC framing,
        # as a stdio client would
        async with Client(server._server, mode="legacy") as client:
            tools = await client.list_tools()
            assert len(tools.tools) > 0

            result = await client.call_tool("vibemk_debug_checkmk_connection", {})

        assert result.is_error is False
        assert len(result.content) > 0
        content_text = result.content[0].text
        assert "✅" in content_text or "Connection successful" in content_text

    def test_host_operations_workflow(self, real_client):
        """Test complete host operations workflow"""
        # This test should only run if we have a test host available
        test_host = os.environ.get("TEST_HOST_NAME")
        if not test_host:
            pytest.skip("TEST_HOST_NAME not provided for host operations test")

        try:
            host_status = real_client.get(f"objects/host/{test_host}", params={"columns": ["state", "plugin_output"]})
        except CheckMKNotFoundError:
            # Host doesn't exist, which is also a valid test result
            return

        assert host_status["success"] is True
        assert "extensions" in host_status["data"]

    def test_service_discovery_workflow(self, real_client):
        """Test reading the service discovery result if a test host is available"""
        test_host = os.environ.get("TEST_HOST_NAME")
        if not test_host:
            pytest.skip("TEST_HOST_NAME not provided for service discovery test")

        # Read-only: starting a discovery run would change the host's services
        discovery_result = real_client.get(f"objects/service_discovery/{test_host}")

        assert discovery_result["success"] is True
        assert "extensions" in discovery_result["data"]

    def test_error_handling_with_invalid_host(self, real_client):
        """Test error handling with invalid host"""
        with pytest.raises(CheckMKNotFoundError) as error:
            real_client.get("objects/host/definitely-not-existing-host-12345")

        assert error.value.status_code == 404

    def test_authentication_validation(self):
        """Test authentication validation"""
        # Create client with invalid credentials
        invalid_config = CheckMKConfig(
            server_url=os.environ.get("CHECKMK_SERVER_URL", "http://localhost:8080"),
            site=os.environ.get("CHECKMK_SITE", "cmk"),
            username="invalid_user",
            password="invalid_password",
        )

        invalid_client = CheckMKClient(invalid_config)

        with pytest.raises(CheckMKAuthenticationError):
            invalid_client.get("version")


class TestLoadTesting:
    """Load testing for vibeMK (optional)"""

    def test_concurrent_requests_load(self, real_client):
        """Test handling multiple concurrent requests"""

        def get_version(_: int) -> bool:
            try:
                return bool(real_client.get("version").get("success"))
            except Exception:
                return False

        # The client blocks, so concurrency has to come from threads
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(get_version, range(10)))

        # At least some should succeed (depending on server load)
        assert sum(results) > 0

    def test_rapid_sequential_requests(self, real_client):
        """Test rapid sequential requests"""
        # Make 20 rapid sequential requests
        success_count = 0
        for _ in range(20):
            try:
                result = real_client.get("version")
                if result.get("success"):
                    success_count += 1
            except Exception:
                # Some failures are acceptable under load
                pass

        # Most should succeed
        assert success_count >= 15  # 75% success rate minimum
