# API Connectivity Test Suite

This comprehensive test suite provides thorough testing of the Robinhood API connectivity, covering all aspects from connection establishment to error handling and performance validation.

## Test Structure

### Test Categories

The test suite is organized into several key categories:

#### 1. **Connection Establishment & Verification Tests** (6 tests)
- Basic network connectivity to API endpoints
- SSL/TLS certificate validation
- HTTP connection pooling verification
- Keep-alive connection testing
- Network timeout handling
- Retry mechanism testing

#### 2. **Authentication Flow Testing** (6 tests)
- Sandbox authentication flow validation
- Production authentication flow testing
- Private key authentication testing
- Public key authentication testing
- Authentication status persistence
- Session management testing

#### 3. **Request/Response Handling Tests** (7 tests)
- 200 OK response handling
- 401 Unauthorized handling
- 429 Rate limit handling
- 5xx Server error handling
- JSON schema validation
- Content-Type header verification
- Response size and compression testing

#### 4. **Error Handling Scenarios** (7 tests)
- DNS resolution failure handling
- Connection refused scenarios
- Network timeout recovery
- Rate limiting detection and handling
- Authentication failure recovery
- Malformed response handling
- Server error recovery (5xx)

#### 5. **Integration Test Coverage** (5 tests)
- End-to-end trading workflow
- Market data integration
- Component interaction testing
- Concurrent request handling
- Memory and resource usage validation

### Test Types

#### Unit Tests
- **Location**: `tests/unit/`
- **Framework**: pytest with unittest.mock
- **Coverage**: Business logic, error handling, configuration
- **Mocking**: HTTP requests, external APIs, file systems

#### Integration Tests
- **Location**: `tests/integration/`
- **Framework**: pytest-asyncio for async testing
- **Coverage**: End-to-end workflows, real API interactions
- **Environment**: Separate sandbox and production configurations

## Test Files

### Core Test Files

| File | Description | Test Type |
|------|-------------|-----------|
| `tests/integration/test_api_connectivity.py` | Main integration tests implementing 25 test cases | Integration |
| `tests/integration/test_utils.py` | Test utilities for API validation and environment setup | Utilities |
| `tests/integration/base_test.py` | Base classes for integration testing | Base Classes |
| `tests/unit/test_api_connectivity_unit.py` | Enhanced unit tests with comprehensive mocking | Unit |
| `tests/unit/test_robinhood_auth.py` | Authentication unit tests | Unit |
| `tests/unit/test_robinhood_client.py` | Client functionality unit tests | Unit |

### Support Files

| File | Description |
|------|-------------|
| `tests/conftest.py` | Pytest configuration and shared fixtures |
| `tests/mocks/api_mocks.py` | Comprehensive API mocking framework |
| `tests/utils/base_test.py` | Base test classes and utilities |

## Running Tests

### Prerequisites

1. **Environment Setup**:
   ```bash
   # Install test dependencies
   pip install -r requirements.txt

   # Set up test environment variables (optional)
   export ROBINHOOD_SANDBOX=true
   export LOG_LEVEL=DEBUG
   ```

2. **Configuration**:
   - Tests use sandbox environment by default
   - Production tests require valid API credentials
   - Network tests require internet connectivity

### Test Execution Commands

#### Run All Tests
```bash
# Run complete test suite
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test categories
pytest tests/ -v -m "unit"        # Unit tests only
pytest tests/ -v -m "integration"  # Integration tests only
pytest tests/ -v -m "performance"  # Performance tests only
```

#### Run Specific Test Files
```bash
# Unit tests
pytest tests/unit/test_robinhood_auth.py -v
pytest tests/unit/test_robinhood_client.py -v
pytest tests/unit/test_api_connectivity_unit.py -v

# Integration tests
pytest tests/integration/test_api_connectivity.py -v
```

#### Run Tests by Category
```bash
# Authentication tests
pytest tests/ -v -m "auth"

# Network connectivity tests
pytest tests/ -v -m "network"

# Error handling tests
pytest tests/ -v -m "error"

# Performance tests
pytest tests/ -v -m "performance"
```

#### Run Tests with Different Configurations
```bash
# Run with specific log level
LOG_LEVEL=DEBUG pytest tests/ -v -s

# Run integration tests only (requires network)
pytest tests/ -v -m "integration and network"

# Run slow tests
pytest tests/ -v -m "slow"
```

### Test Environment Configuration

#### Sandbox Testing
- Uses sandbox API endpoints
- No real money or positions affected
- Safe for development and testing
- Default test environment

#### Production Testing
- Requires valid API credentials
- Tests against live API
- Should be used carefully
- Run with: `ROBINHOOD_SANDBOX=false pytest tests/ -m "integration"`

## Test Results and Reporting

### Coverage Reports
```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Generate XML coverage report (for CI)
pytest tests/ --cov=src --cov-report=xml

# Console coverage report
pytest tests/ --cov=src --cov-report=term-missing
```

### Test Markers and Filtering

#### Available Markers
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.network` - Network tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.error` - Error handling tests

#### Filtering Examples
```bash
# Run only unit tests
pytest tests/ -m "unit"

# Skip slow tests
pytest tests/ -m "not slow"

# Run specific combination
pytest tests/ -m "integration and not slow"
```

## Test Data Management

### Mock Data
- Comprehensive mock responses in `tests/mocks/api_mocks.py`
- Realistic test data that matches API response formats
- Configurable error scenarios and network conditions

### Test Fixtures
- Shared fixtures in `tests/conftest.py`
- Environment setup and teardown
- Temporary file management
- Test data factories

### Cleanup
- Automatic cleanup of test data
- Environment restoration after tests
- Temporary file removal

## Performance Testing

### Load Testing
- Concurrent request handling
- Response time benchmarks
- Memory usage validation
- Connection pooling tests

### Performance Metrics
- Response time measurement
- Request throughput
- Error rates
- Memory consumption

### Benchmarks
- Response time targets (< 5s for API calls)
- Concurrent request handling (10+ concurrent requests)
- Memory usage limits (< 100MB additional usage)

## Error Handling and Edge Cases

### Network Errors
- DNS resolution failures
- Connection timeouts
- Connection refused
- Network unreachable

### API Errors
- Authentication failures
- Rate limiting (429 errors)
- Server errors (5xx)
- Malformed responses

### Data Errors
- Invalid JSON responses
- Missing required fields
- Type mismatches
- Empty responses

## Debugging Tests

### Logging
```bash
# Run with debug logging
LOG_LEVEL=DEBUG pytest tests/ -v -s

# Run specific test with logging
LOG_LEVEL=DEBUG pytest tests/integration/test_api_connectivity.py::TestConnectionEstablishment::test_tc_conn_001_basic_network_connectivity -v -s
```

### Test Selection
```bash
# Run failed tests only
pytest tests/ --lf

# Run last failed tests
pytest tests/ --ff

# Run tests matching pattern
pytest tests/ -k "test_tc_conn_001"
```

## Continuous Integration

### CI/CD Pipeline Integration
- **Pre-commit**: Unit tests only
- **Pull Requests**: Unit + integration tests
- **Main Branch**: Full test suite including performance tests

### Environment Variables for CI
```bash
export ROBINHOOD_SANDBOX=true
export LOG_LEVEL=INFO
export PYTEST_ADDOPTS="--cov=src --cov-report=xml"
```

## Troubleshooting

### Common Issues

#### 1. Network Connectivity Issues
```bash
# Check network connectivity
pytest tests/integration/test_utils.py::NetworkConnectivityTester::test_dns_resolution -v

# Test with mocked network
pytest tests/unit/test_api_connectivity_unit.py -v -m "network"
```

#### 2. Authentication Issues
```bash
# Check authentication configuration
pytest tests/unit/test_robinhood_auth.py -v

# Test with environment variables
ROBINHOOD_API_KEY=test_key ROBINHOOD_PUBLIC_KEY=test_key pytest tests/ -m "auth" -v
```

#### 3. Performance Issues
```bash
# Run performance tests individually
pytest tests/integration/test_api_connectivity.py -v -m "performance"

# Check for memory leaks
pytest tests/unit/test_api_connectivity_unit.py::TestPerformanceMocking -v
```

### Test Debugging Tips

1. **Use `-v -s` flags** for verbose output
2. **Check environment variables** before running tests
3. **Run tests individually** to isolate failures
4. **Use mocked tests** when network is unavailable
5. **Check log files** for detailed error information

## Contributing

### Adding New Tests

1. **Follow naming conventions**:
   - Test functions: `test_tc_[category]_[number]_[description]`
   - Test classes: `Test[Category]`

2. **Add appropriate markers**:
   ```python
   @pytest.mark.integration
   @pytest.mark.network
   async def test_new_integration_test(self):
       # Test implementation
   ```

3. **Include proper documentation**:
   - Test purpose and preconditions
   - Expected outcomes
   - Implementation details

4. **Add cleanup**:
   - Clean up test data
   - Restore environment state
   - Close connections

### Test Maintenance

- **Regular updates** to match API changes
- **Review and update** mock data
- **Monitor test performance** and optimize slow tests
- **Update coverage targets** as codebase grows

## Success Criteria

### Reliability
- All tests pass consistently
- Tests run in reasonable time (< 30 minutes)
- No flaky tests

### Coverage
- 85%+ code coverage for API-related functionality
- All critical paths tested
- Edge cases covered

### Performance
- Tests complete within acceptable time limits
- No memory leaks
- Efficient resource usage

### Maintainability
- Tests are easy to update and extend
- Clear test documentation
- Good separation of concerns

## Support

For issues with the test suite:
1. Check the troubleshooting section
2. Review test logs for error details
3. Run tests individually to isolate issues
4. Check environment configuration
5. Verify network connectivity for integration tests

The test suite is designed to be robust, maintainable, and provide comprehensive coverage of the API connectivity functionality.