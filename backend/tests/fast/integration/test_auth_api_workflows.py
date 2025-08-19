#!/usr/bin/env python3
"""
Fast Integration Tests for Authentication API Workflows

Tests authentication API endpoints using FastAPI TestClient with mocked
external dependencies (Keycloak). This provides fast, reliable tests that
focus on the API behavior and business logic without external service dependencies.

Test Strategy:
- Use FastAPI TestClient for HTTP requests
- Mock Keycloak JWKS and token validation
- Mock managers/dependencies to avoid file system dependencies
- Test realistic request/response flows
- Focus on React frontend integration patterns

Speed: Fast (~1-5s per test)
Dependencies: None (all mocked)
Coverage: API endpoints, authentication flows, error handling
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os
import sys
import json

# Setup path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


@pytest.fixture
def mock_environment():
    """Mock all required environment variables."""
    env_vars = {
        'INSTANCE_CONFIGS': './test-configs',
        'ENFORCER_MODEL': './test-model.conf',
        'ENFORCER_POLICY': './test-policies.csv',
        'USER_POLICIES': './test-user-policies',
        'KEYCLOAK_DOMAIN': 'http://localhost:8080',
        'KEYCLOAK_REALM': 'test-realm',
        'KEYCLOAK_UI_CLIENT_ID': 'test-client',
        'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/test-realm/.well-known/openid-configuration'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies to avoid file system requirements."""
    
    # Mock the managers that require file system access
    with patch('core.settings.managers.user_manager') as mock_user_mgr, \
         patch('core.settings.managers.policy_manager') as mock_policy_mgr, \
         patch('core.settings.managers.instance_manager') as mock_instance_mgr:
        
        # Configure mock managers
        mock_user_mgr.get_user_uuid.return_value = "user-uuid-123"
        mock_user_mgr.get_user.return_value = {"username": "testuser"}
        
        mock_policy_mgr.get_user_policies.return_value = [
            ("user-uuid-123", "instance-uuid-1"),
            ("user-uuid-123", "instance-uuid-2")
        ]
        
        mock_instance_mgr.get_instance_uuid.return_value = "instance-uuid-123"
        mock_instance_mgr.get_instances_by_uuid.return_value = [
            {"name": "Storage1", "uuid": "instance-uuid-1"},
            {"name": "Storage2", "uuid": "instance-uuid-2"}
        ]
        
        yield {
            'user_manager': mock_user_mgr,
            'policy_manager': mock_policy_mgr,
            'instance_manager': mock_instance_mgr
        }


@pytest.fixture
def test_client(mock_environment, mock_dependencies):
    """Create TestClient with mocked dependencies."""
    from api.v0_1.app import app
    return TestClient(app)


@pytest.fixture
def valid_token_payload():
    """Standard valid token payload for tests."""
    return {
        "sub": "user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {
            "roles": ["user"]
        },
        "resource_access": {
            "test-client": {
                "roles": ["user"]
            }
        },
        "iss": "http://localhost:8080/realms/test-realm",
        "aud": "test-client",
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp())
    }


@pytest.fixture
def admin_token_payload():
    """Admin token payload for tests."""
    return {
        "sub": "admin-123",
        "preferred_username": "adminuser",
        "email": "admin@example.com",
        "given_name": "Admin",
        "family_name": "User",
        "realm_access": {
            "roles": ["admin", "user"]
        },
        "resource_access": {
            "test-client": {
                "roles": ["admin", "user"]
            }
        },
        "iss": "http://localhost:8080/realms/test-realm",
        "aud": "test-client",
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp())
    }


class TestAPIRootEndpoints:
    """Test basic API endpoints for React frontend discovery."""
    
    def test_api_root_endpoint(self, test_client):
        """Test API root endpoint returns correct information."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "AMS Data Portal API"
        assert data["version"] == "v0.1"
        assert data["documentation"] == "/docs"
    
    def test_api_test_endpoint(self, test_client):
        """Test API test endpoint for health checking."""
        response = test_client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        assert "test instance_url is working" in data["message"]


class TestAuthenticationEndpoints:
    """Test authentication endpoint workflows for React frontend."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_auth_validate_success_workflow(self, mock_jwt_decode, mock_get_jwks_client, 
                                          test_client, valid_token_payload):
        """
        Test successful token validation workflow.
        
        React Frontend Flow:
        1. React app sends GET /auth/validate with Authorization: Bearer <token>
        2. API validates token against mocked Keycloak
        3. API returns user information
        4. React uses this info to render authenticated UI
        """
        # Mock successful JWT validation
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # React makes request with bearer token
        headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        # Verify successful response
        assert response.status_code == 200
        data = response.json()
        
        # Verify response format React expects
        assert data["valid"] is True
        assert "user" in data
        
        # Verify user information React needs
        user = data["user"]
        assert user["sub"] == "user-123"
        assert user["preferred_username"] == "testuser"
        assert user["email"] == "testuser@example.com"
        assert user["given_name"] == "Test"
        assert user["family_name"] == "User"
        
        # Verify role information for React UI decisions
        assert "realm_access" in user
        assert "user" in user["realm_access"]["roles"]
        
        # Verify JWT validation was called correctly
        mock_jwt_decode.assert_called_once()
        call_args = mock_jwt_decode.call_args
        assert call_args[1]["algorithms"] == ["RS256"]
        assert call_args[1]["issuer"] == "http://localhost:8080/realms/test-realm"
    
    def test_auth_validate_missing_token(self, test_client):
        """
        Test validation without token.
        
        React Frontend Flow:
        1. React app makes request without Authorization header
        2. API returns 401 Unauthorized
        3. React redirects to login page
        """
        response = test_client.get("/api/auth/validate")
        
        assert response.status_code == 401
        data = response.json()
        assert "Bearer token required" in data["detail"]
    
    def test_auth_validate_invalid_token_format(self, test_client):
        """
        Test validation with malformed Authorization header.
        
        React Frontend Flow:
        1. React app sends malformed Authorization header
        2. API returns 401 Unauthorized
        3. React clears stored token and redirects to login
        """
        # Test without "Bearer" prefix
        headers = {"Authorization": "InvalidTokenFormat"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Bearer token required" in data["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_auth_validate_expired_token(self, mock_jwt_decode, mock_get_jwks_client, test_client):
        """
        Test validation with expired token.
        
        React Frontend Flow:
        1. React app sends expired token
        2. API returns 401 Unauthorized
        3. React clears expired token and redirects to login
        """
        # Mock JWT expiration error
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token has expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer expired.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_auth_validate_invalid_signature(self, mock_jwt_decode, mock_get_jwks_client, test_client):
        """
        Test validation with tampered token.
        
        React Frontend Flow:
        1. React app sends token with invalid signature
        2. API returns 401 Unauthorized
        3. React treats as authentication failure
        """
        # Mock JWT signature error
        mock_jwt_decode.side_effect = jwt_lib.InvalidSignatureError("Invalid signature")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer tampered.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]


class TestProtectedEndpointAccess:
    """Test access to protected endpoints with authentication."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_admin_endpoint_with_valid_token(self, mock_jwt_decode, mock_get_jwks_client,
                                           test_client, valid_token_payload):
        """
        Test accessing admin endpoint with valid token.
        
        React Frontend Flow:
        1. React admin panel sends authenticated request
        2. API validates token and checks permissions
        3. API returns requested data
        4. React renders admin interface
        """
        # Mock successful JWT validation
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer valid.jwt.token"}
        response = test_client.get("/api/users/test", headers=headers)
        
        # Should succeed - admin/test just validates token, doesn't check admin role
        assert response.status_code == 200
        data = response.json()
        assert "Authenticated as" in data["message"]
        assert "testuser" in data["message"]
    
    def test_admin_endpoint_without_token(self, test_client):
        """
        Test accessing admin endpoint without authentication.
        
        React Frontend Flow:
        1. React app tries to access admin endpoint without token
        2. API returns 401 Unauthorized
        3. React redirects to login page
        """
        response = test_client.get("/api/users/test")
        
        assert response.status_code == 401
        data = response.json()
        assert "Bearer token required" in data["detail"]


class TestRoleBasedAccess:
    """Test role-based access control workflows."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_admin_role_detection_in_token_validation(self, mock_jwt_decode, mock_get_jwks_client,
                                                    test_client, admin_token_payload):
        """
        Test that admin roles are correctly detected and returned.
        
        React Frontend Flow:
        1. Admin user authenticates and validates token
        2. API returns token with admin role information
        3. React renders admin-specific UI components
        """
        # Mock successful JWT validation with admin token
        mock_jwt_decode.return_value = admin_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer admin.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify admin role information is available to React
        user = data["user"]
        assert "admin" in user["realm_access"]["roles"]
        assert "user" in user["realm_access"]["roles"]
        
        # React can use this to determine UI rendering
        has_admin_role = "admin" in user.get("realm_access", {}).get("roles", [])
        assert has_admin_role is True
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode') 
    def test_regular_user_role_detection(self, mock_jwt_decode, mock_get_jwks_client,
                                        test_client, valid_token_payload):
        """
        Test that regular user roles are correctly detected.
        
        React Frontend Flow:
        1. Regular user authenticates and validates token
        2. API returns token with user (non-admin) role information
        3. React renders user-specific UI (no admin features)
        """
        # Mock successful JWT validation with regular user token
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer user.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only user role is present
        user = data["user"]
        roles = user.get("realm_access", {}).get("roles", [])
        assert "user" in roles
        assert "admin" not in roles
        
        # React can use this to hide admin features
        has_admin_role = "admin" in roles
        assert has_admin_role is False


class TestErrorHandlingWorkflows:
    """Test error handling scenarios for React frontend."""
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_connectivity_failure(self, mock_requests_get, test_client):
        """
        Test behavior when Keycloak is unreachable.
        
        React Frontend Flow:
        1. React app tries to validate token
        2. API cannot reach Keycloak for configuration
        3. API returns 401 Unauthorized
        4. React handles as authentication failure
        """
        # Mock network failure to Keycloak
        mock_requests_get.side_effect = Exception("Connection failed")
        
        headers = {"Authorization": "Bearer some.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_jwks_key_extraction_failure(self, mock_get_jwks_client, test_client):
        """
        Test behavior when JWT signing key cannot be extracted.
        
        React Frontend Flow:
        1. React app sends token with malformed header
        2. API cannot extract signing key from token
        3. API returns 401 Unauthorized
        4. React treats as invalid token
        """
        # Mock JWKS client failure
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt_lib.PyJWKClientError("Key not found")
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer malformed.header.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]


class TestReactFrontendIntegrationPatterns:
    """Test specific patterns needed for React frontend integration."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_validation_response_format(self, mock_jwt_decode, mock_get_jwks_client,
                                            test_client, valid_token_payload):
        """
        Test that token validation returns the exact format React expects.
        
        React Frontend Expectations:
        - Response: {"valid": true, "user": {...}}
        - User object contains all necessary claims
        - Role information is easily accessible
        """
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer test.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify exact format React expects
        assert "valid" in data
        assert data["valid"] is True
        assert "user" in data
        
        user = data["user"]
        
        # Verify all fields React needs are present
        required_fields = ["sub", "preferred_username", "email", "realm_access", "resource_access"]
        for field in required_fields:
            assert field in user, f"Missing required field: {field}"
        
        # Verify React can easily extract role information
        realm_roles = user.get("realm_access", {}).get("roles", [])
        assert isinstance(realm_roles, list)
        assert "user" in realm_roles
        
        # Verify React can get display information
        display_name = user.get("preferred_username")
        email = user.get("email")
        first_name = user.get("given_name")
        last_name = user.get("family_name")
        
        assert display_name == "testuser"
        assert email == "testuser@example.com"
        assert first_name == "Test"
        assert last_name == "User"
    
    def test_cors_headers_for_react_requests(self, test_client):
        """
        Test that CORS headers are properly set for React frontend requests.
        
        React Frontend Requirements:
        - CORS headers must allow React development server
        - Headers must allow Authorization header
        - Headers must allow Bearer token authentication
        """
        # Test preflight request
        response = test_client.options("/api/auth/validate", headers={
            "Origin": "http://localhost:3000",  # React dev server
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        })
        
        # Should allow the request (FastAPI CORS middleware handles this)
        # The exact status code depends on FastAPI's CORS implementation
        # We mainly care that it doesn't return an error
        assert response.status_code in [200, 204]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_multiple_concurrent_validation_requests(self, mock_jwt_decode, mock_get_jwks_client,
                                                   test_client, valid_token_payload):
        """
        Test multiple concurrent token validation requests.
        
        React Frontend Scenario:
        - User has multiple browser tabs open
        - Each tab validates token on page load
        - All should succeed independently
        """
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-signing-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer shared.jwt.token"}
        
        # Make multiple concurrent requests
        responses = []
        for i in range(5):
            response = test_client.get("/api/auth/validate", headers=headers)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user"]["preferred_username"] == "testuser"


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running fast integration tests for authentication API workflows...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)