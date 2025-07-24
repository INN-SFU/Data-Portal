# AMS Data Portal Testing Framework

Speed-first test design for rapid development feedback and reliable CI.

## Quick Start

```bash
# Fast development feedback (<30s)
./run-tests fast

# Authentication tests (fast + slow)
./run-tests auth  

# Integration tests with Docker setup
./run-tests slow --setup

# Full CI suite  
./run-tests all --ci
```

## Test Structure

```
tests/
├── fast/                    # <30s, no external deps
│   ├── unit/               # Pure logic, mocked
│   │   ├── auth/           # Authentication logic
│   │   ├── api/            # API logic  
│   │   └── core/           # Core business logic
│   └── contract/           # API contracts with mocked services
│       ├── auth/           # Auth endpoint behavior
│       └── api/            # API endpoint behavior
├── slow/                   # >30s, requires services
│   ├── integration/        # Real service integration
│   │   ├── auth/           # Real Keycloak tests
│   │   └── api/            # Real API tests
│   └── system/            # Full system tests
├── infra/                  # Test infrastructure  
│   ├── docker/            # Docker service configs
│   ├── fixtures/          # Test data
│   └── helpers/           # Test utilities
└── legacy/                 # Existing tests (gradually migrate)
```

## Test Levels

### Fast Tests (`./run-tests fast`)
- **Target**: <30 seconds total
- **Dependencies**: None (fully mocked)
- **Use Cases**: 
  - Development workflow
  - Pre-commit hooks
  - Quick validation

### Slow Tests (`./run-tests slow`)
- **Target**: Comprehensive coverage
- **Dependencies**: Real services (Keycloak, databases)
- **Use Cases**:
  - Pre-merge validation  
  - Integration verification
  - Full system testing

### Auth Tests (`./run-tests auth`)
- **Target**: All authentication functionality
- **Dependencies**: Fast tests + optional real Keycloak
- **Use Cases**:
  - Authentication development
  - Security testing
  - Auth regression testing

## Development Workflow

### Daily Development
```bash
# Work on feature
./run-tests fast        # Quick feedback (30s)

# Before commit  
./run-tests auth        # Auth-specific validation

# Before merge request
./run-tests slow --setup  # Full validation
```

### CI Pipeline
```bash
# Pull request validation
./run-tests all --ci

# Deploy validation  
./run-tests slow --setup
```

## Service Dependencies

### Fast Tests
- ✅ No dependencies
- ✅ Always work
- ✅ Run anywhere

### Slow Tests  
- 🐳 Docker (for `--setup`)
- 🔑 Keycloak (localhost:8081 when using Docker)
- ⚡ Network access

## Migration Strategy

Gradually migrate from `legacy/` to organized structure:

1. **Immediate**: Use fast tests for new development
2. **Short-term**: Migrate critical tests to fast/slow structure  
3. **Long-term**: Retire legacy tests as coverage improves

## Best Practices

### Fast Tests
- Mock all external dependencies
- Test business logic, not infrastructure
- Keep total runtime <30s
- Use clear, descriptive test names

### Slow Tests
- Test real service interactions
- Verify integration points
- Test error scenarios
- Document service requirements

### Contract Tests
- Test API behavior without real services
- Mock external dependencies
- Verify request/response formats
- Test error handling

## Examples

### Fast Unit Test
```python
def test_bearer_token_prioritization():
    # Test pure logic, no HTTP calls
    token = get_token_from_request(mock_request, mock_credentials)
    assert token == "bearer_token"
```

### Fast Contract Test
```python  
def test_auth_endpoint_returns_401_on_invalid_token():
    # Test API behavior with mocked JWT validation
    with pytest.raises(HTTPException) as exc:
        mock_auth_endpoint(invalid_token)
    assert exc.value.status_code == 401
```

### Slow Integration Test
```python
@pytest.mark.integration
def test_real_keycloak_jwt_validation():
    # Test with real Keycloak instance
    token = get_real_token_from_keycloak()
    result = validate_token_with_real_jwks(token)
    assert result["preferred_username"] == "testuser"
```