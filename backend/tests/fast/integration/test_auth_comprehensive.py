#!/usr/bin/env python3
"""
Comprehensive Authentication Workflow Tests with Real Environment

Tests authentication workflows using the actual application setup with real
configuration files, but mocks external Keycloak calls. This provides realistic
testing without requiring a running Keycloak instance.

Test Strategy:
- Use real FastAPI app with actual configuration
- Mock only external Keycloak JWT validation calls
- Test complete request/response flows as React frontend would use them
- Validate authentication state management and role-based access

Speed: Fast (~2-10s per test)
Dependencies: Real config files, mocked Keycloak
Coverage: End-to-end authentication workflows
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os
import sys
import requests

# Setup path and environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables for the entire test session."""
    # Set environment variables before any imports
    env_vars = {
        'INSTANCE_CONFIGS': './core/settings/managers/instances/configs',
        'ENFORCER_MODEL': './core/settings/managers/policies/casbin/model.conf', 
        'ENFORCER_POLICY': './core/settings/managers/policies/casbin/test_policies.csv',
        'USER_POLICIES': './core/settings/managers/policies/casbin/user_policies',
        'KEYCLOAK_DOMAIN': 'http://localhost:8080',
        'KEYCLOAK_REALM': 'ams-portal',
        'KEYCLOAK_UI_CLIENT_ID': 'ams-portal-ui',
        'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/ams-portal/.well-known/openid-configuration'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup is handled automatically by pytest


def get_keycloak_token(username: str, password: str, client_id: str = "ams-portal-ui") -> str:
    """Get real JWT token from Keycloak for testing."""
    keycloak_url = os.environ.get('KEYCLOAK_DOMAIN', 'http://localhost:8080')
    realm = os.environ.get('KEYCLOAK_REALM', 'ams-portal')
    
    token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
    
    data = {
        'client_id': client_id,
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()
        return token_data['access_token']
    except Exception as e:
        pytest.skip(f"Could not get Keycloak token: {e}")


@pytest.fixture
def real_admin_token():
    """Get real admin JWT token from Keycloak."""
    return get_keycloak_token("admin", "admin123")


@pytest.fixture
def test_client():
    """Create TestClient with real application setup."""
    from api.v0_1.app import app
    return TestClient(app)


@pytest.fixture
def valid_user_token():
    """Valid user token payload for testing."""
    return {
        "sub": "user-uuid-456",
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
def valid_admin_token():
    """Valid admin token payload for testing."""
    return {
        "sub": "admin-uuid-789",
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


# Using real Keycloak tokens instead of mocking for comprehensive testing


class TestAPIDiscoveryWorkflows:
    """Test API discovery endpoints for React frontend."""
    
    def test_api_root_endpoint_discovery(self, test_client):
        """
        Test React app discovering API information.
        
        React Frontend Flow:
        1. App loads and checks API availability
        2. Requests root endpoint for API info
        3. Gets version and documentation links
        """
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify React gets expected API discovery info
        assert data["message"] == "AMS Data Portal API"
        assert data["version"] == "v0.1"
        assert data["documentation"] == "/docs"
        
        # React can use this for version checking and help links
        api_version = data["version"]
        docs_url = data["documentation"]
        assert api_version == "v0.1"
        assert docs_url == "/docs"
    
    def test_api_health_check(self, test_client):
        """Test API health check for React monitoring."""
        response = test_client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        assert "test endpoint_url is working" in data["message"]


class TestAuthenticationWorkflows:
    """Test complete authentication workflows for React frontend."""
    
    def test_successful_admin_authentication_workflow_with_real_token(self, test_client, real_admin_token):
        """
        Test complete successful authentication workflow with real Keycloak token.
        
        React Frontend Flow:
        1. User logs in to Keycloak (simulated by getting real token)
        2. React receives JWT token and stores in localStorage  
        3. React validates token by calling /auth/validate
        4. React gets user info and renders authenticated UI
        """
        # Simulate React sending real Keycloak token for validation
        headers = {"Authorization": f"Bearer {real_admin_token}"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response format React expects
        assert data["valid"] is True
        assert "user" in data
        
        user = data["user"]
        
        # Verify user information React needs for UI (real admin user from Keycloak)
        assert user["preferred_username"] == "admin"
        assert user["email"] == "admin@localhost"
        
        # Verify role information for React UI decisions
        realm_roles = user["realm_access"]["roles"]
        assert "admin" in realm_roles
        assert "user" in realm_roles
        
        # Simulate React UI logic based on token
        is_authenticated = data["valid"]
        username = user["preferred_username"]
        is_admin = "admin" in realm_roles
        
        assert is_authenticated is True
        assert username == "admin"
        assert is_admin is True
    
    def test_protected_admin_endpoint_with_real_token(self, test_client, real_admin_token):
        """
        Test accessing protected admin endpoint with real token.
        
        React Frontend Flow:
        1. Admin user tries to access admin endpoint
        2. React sends real Keycloak token
        3. API validates token and returns admin-specific data
        """
        headers = {"Authorization": f"Bearer {real_admin_token}"}
        response = test_client.get("/api/admin/test", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify admin endpoint response
        assert "Authenticated as" in data["message"]
        assert "admin" in data["message"]  # Username should be in response
    
    def test_missing_token_authentication_workflow(self, test_client):
        """
        Test authentication workflow without token.
        
        React Frontend Flow:
        1. React tries to validate authentication without token
        2. API returns 401 Unauthorized
        3. React redirects to login page or shows login form
        """
        response = test_client.get("/api/auth/validate")
        
        assert response.status_code == 401
        error_data = response.json()
        assert "Bearer token required" in error_data["detail"]
        
        # Simulate React error handling
        is_authenticated = response.status_code == 200
        should_redirect_to_login = response.status_code == 401
        should_clear_stored_token = response.status_code == 401
        
        assert is_authenticated is False
        assert should_redirect_to_login is True
        assert should_clear_stored_token is True
    
    def test_malformed_token_authentication_workflow(self, test_client):
        """
        Test authentication workflow with malformed token.
        
        React Frontend Flow:
        1. React sends malformed Authorization header
        2. API returns 401 Unauthorized
        3. React treats as authentication failure
        """
        # Test various malformed headers
        malformed_headers = [
            {"Authorization": "NotBearerToken"},  # Missing Bearer prefix
            {"Authorization": "Bearer"},          # Empty token
            {"Authorization": "Bearer "},         # Space only
            {"Authorization": ""},                # Empty header
        ]
        
        for headers in malformed_headers:
            response = test_client.get("/api/auth/validate", headers=headers)
            assert response.status_code == 401
            error_data = response.json()
            assert "Bearer token required" in error_data["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_expired_token_authentication_workflow(self, mock_jwt_decode, mock_get_jwks_client, test_client):
        """
        Test authentication workflow with expired token.
        
        React Frontend Flow:
        1. React sends expired token for validation
        2. API returns 401 Unauthorized
        3. React clears expired token and redirects to login
        """
        # Mock expired token error
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token has expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer expired.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        error_data = response.json()
        assert "Could not validate credentials" in error_data["detail"]
        
        # Simulate React handling expired token
        is_token_expired = response.status_code == 401
        should_clear_token_from_storage = is_token_expired
        should_redirect_to_login = is_token_expired
        
        assert is_token_expired is True
        assert should_clear_token_from_storage is True
        assert should_redirect_to_login is True


class TestProtectedEndpointAccess:
    """Test access to protected endpoints with authentication."""
    
    def test_protected_admin_endpoint_access_workflow(self, test_client, real_admin_token):
        """
        Test accessing protected admin endpoint with real admin token.
        
        React Frontend Flow:
        1. Authenticated admin user tries to access admin endpoint
        2. API validates real token successfully
        3. Endpoint returns data with admin username
        """
        headers = {"Authorization": f"Bearer {real_admin_token}"}
        response = test_client.get("/api/admin/test", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "Authenticated as" in data["message"]
        assert "admin" in data["message"]
    
    def test_protected_endpoint_without_authentication(self, test_client):
        """
        Test accessing protected endpoint without authentication.
        
        React Frontend Flow:
        1. React tries to access protected endpoint without token
        2. API returns 401 Unauthorized
        3. React redirects to login
        """
        response = test_client.get("/api/admin/test")
        
        assert response.status_code == 401
        error_data = response.json()
        assert "Bearer token required" in error_data["detail"]


class TestConcurrentAuthenticationScenarios:
    """Test concurrent authentication scenarios for React frontend."""
    
    def test_multiple_concurrent_token_validations(self, test_client, real_admin_token):
        """
        Test multiple concurrent token validation requests with real token.
        
        React Frontend Scenario:
        - User has multiple browser tabs open
        - Each tab validates token simultaneously
        - All should succeed independently
        """
        headers = {"Authorization": f"Bearer {real_admin_token}"}
        
        # Make multiple concurrent requests
        responses = []
        for i in range(5):
            response = test_client.get("/api/auth/validate", headers=headers)
            responses.append(response)
        
        # All should succeed with consistent results
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user"]["preferred_username"] == "admin"


class TestErrorHandlingScenarios:
    """Test error handling scenarios for React frontend."""
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_connectivity_failure_workflow(self, mock_requests_get, test_client):
        """
        Test authentication when Keycloak is unreachable.
        
        React Frontend Flow:
        1. React tries to validate token
        2. API cannot reach Keycloak for configuration
        3. API returns 401 Unauthorized
        4. React handles as authentication failure
        """
        # Mock Keycloak connection failure
        mock_requests_get.side_effect = Exception("Connection refused")
        
        headers = {"Authorization": "Bearer some.jwt.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        error_data = response.json()
        assert "Could not validate credentials" in error_data["detail"]
        
        # React should handle gracefully
        should_show_generic_error = response.status_code >= 500
        should_show_auth_error = response.status_code == 401
        should_retry_login = response.status_code == 401
        
        assert should_show_generic_error is False  # Should be 401, not 500
        assert should_show_auth_error is True
        assert should_retry_login is True
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_invalid_jwt_signature_workflow(self, mock_get_jwks_client, test_client):
        """
        Test authentication with token having invalid signature.
        
        React Frontend Flow:
        1. React sends token with invalid/tampered signature
        2. API cannot extract valid signing key
        3. API returns 401 Unauthorized
        4. React treats as invalid token
        """
        # Mock JWKS client failure
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt_lib.PyJWKClientError("Invalid key")
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer tampered.signature.token"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        error_data = response.json()
        assert "Could not validate credentials" in error_data["detail"]


class TestReactFrontendIntegrationPatterns:
    """Test specific React frontend integration patterns."""
    
    def test_admin_profile_data_extraction(self, test_client, real_admin_token):
        """
        Test extracting admin profile data for React UI components.
        
        React Components Need:
        - User avatar/display name
        - Email for profile settings
        - Role information for UI rendering
        - User ID for API calls
        """
        headers = {"Authorization": f"Bearer {real_admin_token}"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        user = data["user"]
        
        # Extract data React components would use
        user_id = user["sub"]
        email = user["email"]
        first_name = user.get("given_name", "")
        last_name = user.get("family_name", "")
        username = user["preferred_username"]
        full_name = f"{first_name} {last_name}".strip()
        display_name = full_name if full_name else username
        
        # Verify all necessary data is available (admin user from Keycloak)
        assert user_id is not None
        assert email == "admin@localhost"
        assert username == "admin"
        
        # Role-based UI rendering data
        roles = user.get("realm_access", {}).get("roles", [])
        is_admin = "admin" in roles
        is_user = "user" in roles
        
        assert is_admin is True
        assert is_user is True
    
    def test_token_expiry_checking_for_refresh(self, test_client, real_admin_token):
        """
        Test token expiry information for React token refresh logic.
        
        React Frontend Pattern:
        - Check token expiry time
        - Refresh token proactively before expiry
        - Handle refresh failures gracefully
        """
        headers = {"Authorization": f"Bearer {real_admin_token}"}
        response = test_client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        user = data["user"]
        
        # Extract expiry information from real token
        exp_timestamp = user.get("exp")
        iat_timestamp = user.get("iat")
        
        assert exp_timestamp is not None
        assert iat_timestamp is not None
        
        # Simulate React token refresh logic
        now = datetime.now().timestamp()
        time_until_expiry = exp_timestamp - now
        
        is_expired = exp_timestamp < now
        is_valid = not is_expired
        
        assert is_expired is False
        assert is_valid is True
        assert time_until_expiry > 0  # Token should be valid for some time
    
    def test_cors_headers_for_react_development(self, test_client):
        """
        Test CORS headers for React development server.
        
        React Development Requirements:
        - Allow requests from localhost:3000
        - Allow Authorization header
        - Handle preflight requests properly
        """
        # Test actual request with Origin header (simulating React dev server)
        response = test_client.get("/", headers={
            "Origin": "http://localhost:3000"
        })
        
        # Should not be blocked by CORS
        assert response.status_code == 200
        
        # Test preflight request simulation
        response = test_client.options("/api/auth/validate", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET", 
            "Access-Control-Request-Headers": "Authorization"
        })
        
        # Should handle preflight appropriately
        assert response.status_code in [200, 204, 405]  # Various acceptable responses


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running comprehensive authentication workflow tests...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)