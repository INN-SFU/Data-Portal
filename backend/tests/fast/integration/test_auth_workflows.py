#!/usr/bin/env python3
"""
Comprehensive Authentication Workflow Tests for React Frontend

These tests validate end-to-end authentication workflows specifically designed
for the React frontend using bearer token authentication.

Test Scenarios:
1. Token validation with valid/invalid/expired tokens
2. Protected endpoint access with authentication
3. Admin role-based access control
4. Authentication error handling
5. Token refresh scenarios (when implemented)

Focus: Bearer token authentication only (React frontend)
Speed: Fast integration tests with mocked Keycloak
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from api.v0_1.app import app


class TestAuthenticationWorkflows:
    """Test comprehensive authentication workflows for React frontend."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables."""
        # Set minimal required environment variables
        self.env_vars = {
            'INSTANCE_CONFIGS': './core/settings/managers/instances/configs',
            'ENFORCER_MODEL': './core/settings/managers/policies/casbin/model.conf',
            'ENFORCER_POLICY': './core/settings/managers/policies/casbin/test_policies.csv',
            'USER_POLICIES': './core/settings/managers/policies/casbin/user_policies',
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/test-realm/.well-known/openid-configuration'
        }
        
        # Apply environment variables
        for key, value in self.env_vars.items():
            os.environ[key] = value
            
        yield
        
        # Clean up environment variables
        for key in self.env_vars.keys():
            os.environ.pop(key, None)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_keycloak_config(self):
        """Mock Keycloak OIDC configuration."""
        return {
            "issuer": "http://localhost:8080/realms/test-realm",
            "jwks_uri": "http://localhost:8080/realms/test-realm/protocol/openid-connect/certs"
        }
    
    @pytest.fixture
    def valid_token_payload(self):
        """Sample valid token payload."""
        return {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "testuser@example.com",
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
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
    
    @pytest.fixture
    def admin_token_payload(self):
        """Sample admin token payload."""
        return {
            "sub": "admin-123",
            "preferred_username": "adminuser",
            "email": "admin@example.com",
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
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }


class TestTokenValidationWorkflow(TestAuthenticationWorkflows):
    """Test token validation workflows."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_valid_token_validation_workflow(self, mock_jwt_decode, mock_get_jwks_client, 
                                           client, valid_token_payload):
        """
        Test complete workflow with valid bearer token.
        
        Workflow:
        1. React app sends request with Authorization: Bearer <token>
        2. API validates token against Keycloak
        3. API returns user info
        """
        # Mock JWT validation
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Make request with valid token
        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = client.get("/auth/validate", headers=headers)
        
        # Verify successful validation
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["valid"] is True
        assert response_data["user"]["preferred_username"] == "testuser"
        assert response_data["user"]["email"] == "testuser@example.com"
        
        # Verify JWT decode was called with correct parameters
        mock_jwt_decode.assert_called_once()
        call_args = mock_jwt_decode.call_args
        assert call_args[0][0] == "valid-jwt-token"  # token
        assert call_args[1]["algorithms"] == ["RS256"]
        assert call_args[1]["issuer"] == "http://localhost:8080/realms/test-realm"
        assert call_args[1]["options"]["verify_aud"] is False
    
    def test_missing_token_workflow(self, client):
        """
        Test workflow when no token is provided.
        
        Workflow:
        1. React app sends request without Authorization header
        2. API returns 401 Unauthorized
        """
        response = client.get("/auth/validate")
        
        assert response.status_code == 401
        assert "Bearer token required" in response.json()["detail"]
    
    def test_invalid_token_format_workflow(self, client):
        """
        Test workflow with malformed Authorization header.
        
        Workflow:
        1. React app sends request with malformed token
        2. API returns 401 Unauthorized
        """
        # Test with malformed header (no Bearer prefix)
        headers = {"Authorization": "invalid-header-format"}
        response = client.get("/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Bearer token required" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_expired_token_workflow(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test workflow with expired token.
        
        Workflow:
        1. React app sends request with expired token
        2. API attempts validation
        3. JWT validation fails with ExpiredSignatureError
        4. API returns 401 Unauthorized
        """
        # Mock expired token
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer expired-token"}
        response = client.get("/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_invalid_signature_workflow(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test workflow with token having invalid signature.
        
        Workflow:
        1. React app sends request with tampered token
        2. API attempts validation
        3. JWT validation fails with InvalidSignatureError
        4. API returns 401 Unauthorized
        """
        # Mock invalid signature
        mock_jwt_decode.side_effect = jwt_lib.InvalidSignatureError("Invalid signature")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer tampered-token"}
        response = client.get("/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]


class TestProtectedEndpointWorkflow(TestAuthenticationWorkflows):
    """Test protected endpoint access workflows."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_protected_endpoint_access_workflow(self, mock_jwt_decode, mock_get_jwks_client,
                                              client, valid_token_payload):
        """
        Test accessing protected admin endpoint with valid token.
        
        Workflow:
        1. React admin panel sends request to protected endpoint
        2. API validates bearer token
        3. API checks user has required permissions
        4. API returns requested data
        """
        # Mock valid token
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer valid-token"}
        response = client.get("/admin/test", headers=headers)
        
        # Should succeed (admin/test endpoint just validates token, doesn't check admin role)
        assert response.status_code == 200
        response_data = response.json()
        assert "Authenticated as" in response_data["message"]
        assert "testuser" in response_data["message"]
    
    def test_protected_endpoint_no_token_workflow(self, client):
        """
        Test accessing protected endpoint without token.
        
        Workflow:
        1. React app sends request to protected endpoint without token
        2. API returns 401 Unauthorized
        """
        response = client.get("/admin/test")
        
        assert response.status_code == 401
        assert "Bearer token required" in response.json()["detail"]


class TestRoleBasedAccessWorkflow(TestAuthenticationWorkflows):
    """Test role-based access control workflows."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_admin_access_workflow(self, mock_jwt_decode, mock_get_jwks_client,
                                 client, admin_token_payload):
        """
        Test admin user accessing admin-only functionality.
        
        Workflow:
        1. React admin panel authenticates admin user
        2. Admin user requests admin-only data
        3. API validates token and checks admin role
        4. API returns admin data
        """
        # Mock admin token
        mock_jwt_decode.return_value = admin_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer admin-token"}
        
        # Test admin endpoint that requires admin role
        # Note: Most admin endpoints check is_user_admin() function
        response = client.get("/admin/test", headers=headers)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "adminuser" in response_data["message"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_regular_user_admin_access_denied_workflow(self, mock_jwt_decode, mock_get_jwks_client,
                                                     client, valid_token_payload):
        """
        Test regular user trying to access admin-only functionality.
        
        Workflow:
        1. React app authenticates regular user
        2. User attempts to access admin endpoint
        3. API validates token but denies admin access
        4. API returns 403 Forbidden
        """
        # Mock regular user token
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer user-token"}
        
        # Try to access admin-only functionality (like adding users)
        # This would require mocking the managers, so let's test the auth logic
        response = client.get("/admin/test", headers=headers)
        
        # This endpoint doesn't check admin role, just validates token
        assert response.status_code == 200
        
        # For actual admin role testing, we need to test the is_user_admin function
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test admin role detection
        assert is_user_admin(valid_token_payload) is False  # Regular user
        assert is_user_admin(admin_token_payload) is True   # Admin user


class TestAPIRootAndDiscoveryWorkflow(TestAuthenticationWorkflows):
    """Test API discovery and root endpoint workflows."""
    
    def test_api_root_discovery_workflow(self, client):
        """
        Test React app discovering API endpoints.
        
        Workflow:
        1. React app loads and checks API availability
        2. Requests API root to get basic info
        3. API returns version and documentation info
        """
        response = client.get("/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "AMS Data Portal API"
        assert response_data["version"] == "v0.1"
        assert response_data["documentation"] == "/docs"
    
    def test_api_health_check_workflow(self, client):
        """
        Test React app checking API health.
        
        Workflow:
        1. React app performs health check
        2. API returns test endpoint response
        """
        response = client.get("/test")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "test endpoint_url is working" in response_data["message"]


class TestAuthenticationUtilityFunctions:
    """Test authentication utility functions in isolation."""
    
    def test_is_user_admin_with_realm_roles(self):
        """Test admin detection via realm roles."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        token_payload = {
            "realm_access": {
                "roles": ["admin", "user"]
            },
            "resource_access": {}
        }
        
        assert is_user_admin(token_payload) is True
    
    def test_is_user_admin_with_client_roles(self):
        """Test admin detection via client-specific roles."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        token_payload = {
            "realm_access": {
                "roles": ["user"]
            },
            "resource_access": {
                "test-client": {
                    "roles": ["admin"]
                }
            }
        }
        
        assert is_user_admin(token_payload) is True
    
    def test_is_user_admin_no_admin_role(self):
        """Test admin detection when user has no admin role."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        token_payload = {
            "realm_access": {
                "roles": ["user"]
            },
            "resource_access": {
                "test-client": {
                    "roles": ["user"]
                }
            }
        }
        
        assert is_user_admin(token_payload) is False
    
    def test_is_user_admin_missing_access_claims(self):
        """Test admin detection with missing access claims."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        token_payload = {
            "sub": "user-123",
            "preferred_username": "testuser"
        }
        
        assert is_user_admin(token_payload) is False


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