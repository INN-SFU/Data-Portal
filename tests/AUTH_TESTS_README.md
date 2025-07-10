# Authentication Tests

This directory contains comprehensive tests for the authentication system improvements made to the AMS Data Portal.

## Test Structure

### Unit Tests (`unit/test_auth_security_improvements.py`)
Tests individual authentication functions in isolation:

- **Token Validation**: Tests `validate_token_from_cookie()` function
  - Valid token scenarios
  - Missing token handling
  - Expired token detection
  - Invalid token rejection

- **Cookie Security Settings**: Tests `get_cookie_security_settings()` function
  - Development environment (HTTP) settings
  - Production environment (HTTPS) settings  
  - Default configuration behavior

- **Admin Role Detection**: Tests `is_user_admin()` function
  - Realm-level admin roles
  - Client-specific admin roles
  - Regular user scenarios
  - Missing role structures

- **Landing Page Authentication**: Tests authentication state detection
  - Authenticated user scenarios
  - Unauthenticated user scenarios

### Integration Tests (`integration/test_auth_endpoints.py`)
Tests complete authentication flows:

- **Login Callback**: Tests OAuth callback endpoint
  - Successful token exchange with Keycloak
  - Missing authorization code handling
  - Failed token exchange scenarios
  - Cookie setting verification

- **Logout Flow**: Tests logout endpoint
  - Cookie clearing functionality
  - Keycloak logout redirect URL generation
  - Proper parameter encoding

- **Token Refresh**: Tests refresh token endpoint
  - Successful token refresh
  - Missing refresh token handling
  - Invalid refresh token scenarios
  - Cookie updates

- **Landing Page Integration**: Tests full authentication detection
  - Template context for authenticated users
  - Template context for unauthenticated users

## Running Tests

### Quick Start
```bash
# Run all authentication tests
python tests/run_auth_tests.py

# Run only unit tests
python tests/run_auth_tests.py --unit

# Run only integration tests  
python tests/run_auth_tests.py --integration

# Run with verbose output
python tests/run_auth_tests.py --verbose
```

### Manual Test Execution
```bash
# Unit tests only
python -m pytest tests/unit/test_auth_security_improvements.py -v

# Integration tests only
python -m pytest tests/integration/test_auth_endpoints.py -v

# All auth tests
python -m pytest tests/unit/test_auth_security_improvements.py tests/integration/test_auth_endpoints.py -v
```

### Individual Test Files
```bash
# Run unit tests directly
python tests/unit/test_auth_security_improvements.py

# Run integration tests directly  
python tests/integration/test_auth_endpoints.py
```

## Test Coverage

The tests cover the following authentication improvements:

### ✅ Critical Fixes Tested
1. **Landing Page Authentication Check**: Proper token validation instead of cookie presence
2. **Cookie Security Settings**: Environment-based security configuration
3. **Token Validation**: JWT validation with expiry checking
4. **Logout Cookie Clearing**: Consistent cookie deletion parameters

### ✅ New Features Tested
1. **Refresh Token Support**: Complete refresh token flow
2. **Error Handling**: Graceful degradation on failures
3. **Security Utilities**: Reusable authentication functions
4. **Environment Awareness**: Development vs production settings

## Mock Strategy

The tests use comprehensive mocking to isolate functionality:

- **External Dependencies**: Keycloak requests mocked
- **Environment Variables**: Controlled test environment
- **JWT Operations**: Mocked token validation
- **HTTP Responses**: Mocked FastAPI responses
- **Logging**: Mocked for verification

## Test Assertions

Tests verify:
- **Return Values**: Correct data structures and types
- **Side Effects**: Cookie operations, logging calls
- **Error Conditions**: Proper exception handling
- **Integration**: End-to-end flow validation
- **Security**: Proper parameter handling

## Dependencies

### For Core Logic Tests (No Dependencies Required)
```bash
# Run basic authentication logic tests
python3 tests/test_auth_core_logic.py
```

### For Full Test Suite
Tests require:
- `pytest`: Test framework
- `fastapi`: Web framework (TestClient)
- `requests`: HTTP library (mocked)
- `jwt`: Token handling (mocked)
- `unittest.mock`: Mocking utilities

```bash
# Install test dependencies
pip install pytest fastapi[all] requests PyJWT

# Or if using virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
pip install pytest fastapi[all] requests PyJWT
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Authentication Tests
  run: |
    python tests/run_auth_tests.py --verbose
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in Python path
2. **Mock Failures**: Check mock patch decorators match actual imports
3. **Environment Variables**: Tests set required env vars automatically
4. **Timeout Issues**: Increase timeout in test runner if needed

### Test Development

When adding new authentication tests:

1. Follow existing patterns in test files
2. Use appropriate mock decorators
3. Test both success and failure scenarios
4. Include integration tests for new endpoints
5. Update this README with new test descriptions