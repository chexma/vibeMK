# vibeMK Test Suite

Comprehensive test coverage for the vibeMK CheckMK MCP Server.

## 🧪 Test Structure

### Unit Tests
- **`test_api_client.py`** - CheckMK API client functionality
- **`test_config.py`** - Configuration management
- **`test_handlers_hosts.py`** - Host handler operations
- **`test_mcp_server.py`** - MCP server protocol handling

### Integration Tests
- **`test_integration.py`** - End-to-end tests with real CheckMK (optional)

### Test Fixtures
- **`conftest.py`** - Shared fixtures and mock configurations

## 🚀 Running Tests

### Prerequisites

```bash
# Install development dependencies
pip install -e ".[dev]"
```

### Unit Tests (Default)

```bash
# Run all unit tests
pytest

# Run specific test file
pytest tests/test_api_client.py

# Run with coverage
pytest --cov=. --cov-report=html

# Verbose output
pytest -v
```

### Integration Tests (Optional)

Integration tests require a real CheckMK instance:

```bash
# Set environment variables
export INTEGRATION_TESTS=true
export CHECKMK_SERVER_URL="http://your-checkmk:8080"
export CHECKMK_SITE="your_site"
export CHECKMK_USERNAME="automation"
export CHECKMK_PASSWORD="your_password"
export TEST_HOST_NAME="test-server"  # Optional test host

# Run integration tests
pytest tests/test_integration.py
```

### Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Run only handler tests
pytest -m handler

# Skip slow tests
pytest -m "not slow"
```

## 📊 Test Coverage Goals

| Component | Target Coverage | Description |
|-----------|----------------|-------------|
| **API Client** | 95%+ | HTTP client, error handling, retries |
| **Handlers** | 90%+ | Business logic, tool implementations |
| **MCP Server** | 85%+ | Protocol handling, routing |
| **Configuration** | 95%+ | Environment parsing, validation |
| **Overall** | 85%+ | Complete codebase |

## 🎯 Test-Driven Development

### TDD Workflow

1. **Write Test First**
   ```bash
   # Create failing test
   def test_new_feature():
       assert new_feature() == expected_result
   ```

2. **Run Test (Should Fail)**
   ```bash
   pytest tests/test_new_feature.py::test_new_feature -v
   ```

3. **Implement Minimum Code**
   ```python
   def new_feature():
       return expected_result
   ```

4. **Test Passes - Refactor**
   ```bash
   pytest tests/test_new_feature.py::test_new_feature -v
   ```

### TDD Benefits for vibeMK

- **API Integration**: Complex CheckMK API interactions are well-tested
- **Error Handling**: Edge cases and error conditions covered
- **Regression Prevention**: Changes don't break existing functionality
- **Documentation**: Tests serve as usage examples
- **Confidence**: Reliable operation in production environments

## 🔧 Test Configuration

### Pytest Settings (`pytest.ini`)

- **Async Support**: `asyncio_mode = auto`
- **Test Discovery**: Automatic test file detection
- **Markers**: Categorize tests (unit, integration, slow)
- **Coverage**: Optional coverage reporting

### Mock Strategy

```python
# API Client Mocking
@pytest.fixture
def mock_checkmk_client():
    client = MagicMock()
    client.get.return_value = {"success": True, "data": {}}
    return client

# Configuration Mocking
@pytest.fixture
def mock_config():
    return CheckMKConfig(
        server_url="http://test",
        site="test",
        username="test",
        password="test"
    )
```

## 🐛 Testing Scenarios

### Error Conditions
- Network timeouts
- Authentication failures
- Invalid JSON responses
- HTTP error codes (401, 404, 500)
- Malformed requests

### Edge Cases
- Empty responses
- Large datasets
- Special characters in host names
- Concurrent requests
- Rate limiting

### Real-World Scenarios
- Host creation/deletion workflows
- Service discovery processes
- Configuration activation
- Problem acknowledgment
- Downtime scheduling

## 📈 Continuous Integration

### GitHub Actions Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## 🎯 Testing Best Practices

### Do's ✅

- **Write tests first** (TDD approach)
- **Mock external dependencies** (CheckMK API)
- **Test error conditions** extensively
- **Use descriptive test names**
- **Keep tests independent** and isolated
- **Test public interfaces** not implementation details

### Don'ts ❌

- **Don't test implementation details**
- **Don't write flaky tests** (timing dependencies)
- **Don't ignore failing tests**
- **Don't skip error condition testing**
- **Don't write tests without assertions**

### Example Test Structure

```python
class TestHostHandler:
    """Test Host Handler functionality"""

    def test_get_host_status_success(self, host_handler, mock_responses):
        """Test successful host status retrieval"""
        # Arrange
        host_handler.client.get.return_value = mock_responses["host_up"]
        
        # Act
        result = await host_handler.handle("vibemk_get_host_status", {
            "host_name": "test-server"
        })
        
        # Assert
        assert len(result) == 1
        assert "🟢 **UP**" in result[0]["text"]
        assert "test-server" in result[0]["text"]
```

## 🚀 Adding New Tests

### For New Handlers

1. Create `test_handlers_[name].py`
2. Follow existing handler test patterns
3. Mock CheckMK API responses
4. Test all tool functions
5. Include error conditions

### For New API Features

1. Add tests to `test_api_client.py`
2. Mock HTTP responses
3. Test success and error paths
4. Verify proper URL construction
5. Check parameter passing

### For New MCP Tools

1. Add to relevant handler test file
2. Test tool registration
3. Verify parameter validation
4. Check response formatting
5. Test error handling

Happy Testing! 🎉