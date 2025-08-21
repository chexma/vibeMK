"""
Tests for Configuration Management
"""

import pytest
import os
from unittest.mock import patch
from config.settings import CheckMKConfig, MCPConfig


class TestCheckMKConfig:
    """Test CheckMK configuration"""

    def test_config_from_env_complete(self):
        """Test configuration creation from complete environment variables"""
        env_vars = {
            "CHECKMK_SERVER_URL": "https://checkmk.example.com",
            "CHECKMK_SITE": "production",
            "CHECKMK_USERNAME": "automation",
            "CHECKMK_PASSWORD": "secret123",
            "CHECKMK_VERIFY_SSL": "true",
            "CHECKMK_TIMEOUT": "45",
            "CHECKMK_MAX_RETRIES": "5",
        }

        with patch.dict(os.environ, env_vars):
            config = CheckMKConfig.from_env()

            assert config.server_url == "https://checkmk.example.com"
            assert config.site == "production"
            assert config.username == "automation"
            assert config.password == "secret123"
            assert config.verify_ssl is True
            assert config.timeout == 45
            assert config.max_retries == 5

    def test_config_from_env_minimal(self):
        """Test configuration with minimal required environment variables"""
        env_vars = {
            "CHECKMK_SERVER_URL": "http://localhost:8080",
            "CHECKMK_SITE": "cmk",
            "CHECKMK_USERNAME": "automation",
            "CHECKMK_PASSWORD": "password",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = CheckMKConfig.from_env()

            # Required fields
            assert config.server_url == "http://localhost:8080"
            assert config.site == "cmk"
            assert config.username == "automation"
            assert config.password == "password"

            # Default values
            assert config.verify_ssl is True
            assert config.timeout == 30
            assert config.max_retries == 3

    def test_config_missing_required_fields(self):
        """Test configuration with missing required fields"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="CHECKMK_SERVER_URL"):
                CheckMKConfig.from_env()

    def test_config_invalid_boolean(self):
        """Test configuration with invalid boolean value"""
        env_vars = {
            "CHECKMK_SERVER_URL": "http://localhost:8080",
            "CHECKMK_SITE": "cmk",
            "CHECKMK_USERNAME": "automation",
            "CHECKMK_PASSWORD": "password",
            "CHECKMK_VERIFY_SSL": "maybe",  # Invalid boolean
        }

        with patch.dict(os.environ, env_vars):
            config = CheckMKConfig.from_env()
            # Should default to True for invalid boolean
            assert config.verify_ssl is True

    def test_config_invalid_integer(self):
        """Test configuration with invalid integer value"""
        env_vars = {
            "CHECKMK_SERVER_URL": "http://localhost:8080",
            "CHECKMK_SITE": "cmk",
            "CHECKMK_USERNAME": "automation",
            "CHECKMK_PASSWORD": "password",
            "CHECKMK_TIMEOUT": "not_a_number",
        }

        with patch.dict(os.environ, env_vars):
            config = CheckMKConfig.from_env()
            # Should use default value for invalid integer
            assert config.timeout == 30

    def test_config_url_normalization(self):
        """Test URL normalization"""
        test_cases = [
            ("http://checkmk.local", "http://checkmk.local"),
            ("http://checkmk.local/", "http://checkmk.local"),
            ("https://checkmk.local:8080/", "https://checkmk.local:8080"),
            ("checkmk.local", "http://checkmk.local"),  # Should add http
        ]

        for input_url, expected_url in test_cases:
            env_vars = {
                "CHECKMK_SERVER_URL": input_url,
                "CHECKMK_SITE": "cmk",
                "CHECKMK_USERNAME": "automation",
                "CHECKMK_PASSWORD": "password",
            }

            with patch.dict(os.environ, env_vars):
                config = CheckMKConfig.from_env()
                assert config.server_url == expected_url

    def test_config_validation(self):
        """Test configuration validation"""
        # Test invalid timeout
        with pytest.raises(ValueError, match="timeout must be positive"):
            CheckMKConfig(server_url="http://test", site="test", username="user", password="pass", timeout=-1)

        # Test invalid max_retries
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            CheckMKConfig(server_url="http://test", site="test", username="user", password="pass", max_retries=-1)

    def test_config_password_redaction(self):
        """Test that password is redacted in string representation"""
        config = CheckMKConfig(server_url="http://test", site="test", username="user", password="secret123")

        config_str = str(config)
        assert "secret123" not in config_str
        assert "***" in config_str or "[HIDDEN]" in config_str


class TestMCPConfig:
    """Test MCP configuration"""

    def test_mcp_config_creation(self):
        """Test MCP configuration creation"""
        config = MCPConfig(name="test-vibemk", version="0.1.0")

        assert config.name == "test-vibemk"
        assert config.version == "0.1.0"

    def test_mcp_config_defaults(self):
        """Test MCP configuration defaults"""
        config = MCPConfig()

        assert config.name == "vibemk"
        assert config.version.startswith("0.")  # Should have some version

    def test_mcp_config_validation(self):
        """Test MCP configuration validation"""
        # Test invalid name
        with pytest.raises(ValueError, match="name cannot be empty"):
            MCPConfig(name="", version="1.0.0")

        # Test invalid version
        with pytest.raises(ValueError, match="version cannot be empty"):
            MCPConfig(name="test", version="")


class TestConfigurationIntegration:
    """Test configuration integration scenarios"""

    def test_development_environment(self):
        """Test typical development environment configuration"""
        dev_env = {
            "CHECKMK_SERVER_URL": "http://localhost:8080",
            "CHECKMK_SITE": "cmk",
            "CHECKMK_USERNAME": "automation",
            "CHECKMK_PASSWORD": "cmk",
            "CHECKMK_VERIFY_SSL": "false",
            "CHECKMK_TIMEOUT": "10",
        }

        with patch.dict(os.environ, dev_env):
            config = CheckMKConfig.from_env()

            assert config.server_url == "http://localhost:8080"
            assert config.verify_ssl is False
            assert config.timeout == 10

    def test_production_environment(self):
        """Test typical production environment configuration"""
        prod_env = {
            "CHECKMK_SERVER_URL": "https://checkmk.company.com",
            "CHECKMK_SITE": "production",
            "CHECKMK_USERNAME": "vibemk_automation",
            "CHECKMK_PASSWORD": "complex_secure_password_123",
            "CHECKMK_VERIFY_SSL": "true",
            "CHECKMK_TIMEOUT": "60",
            "CHECKMK_MAX_RETRIES": "5",
        }

        with patch.dict(os.environ, prod_env):
            config = CheckMKConfig.from_env()

            assert config.server_url == "https://checkmk.company.com"
            assert config.verify_ssl is True
            assert config.timeout == 60
            assert config.max_retries == 5

    def test_docker_environment(self):
        """Test Docker-style environment configuration"""
        docker_env = {
            "CHECKMK_SERVER_URL": "http://checkmk-container:5000",
            "CHECKMK_SITE": "docker",
            "CHECKMK_USERNAME": "automation",
            "CHECKMK_PASSWORD": "docker_password",
            "CHECKMK_VERIFY_SSL": "false",
        }

        with patch.dict(os.environ, docker_env):
            config = CheckMKConfig.from_env()

            assert "checkmk-container" in config.server_url
            assert config.verify_ssl is False
