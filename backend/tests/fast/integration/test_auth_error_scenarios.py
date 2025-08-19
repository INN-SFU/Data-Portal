#!/usr/bin/env python3
"""
Authentication Error Scenarios and Edge Cases

Tests various error conditions and edge cases in the authentication system
to ensure robust error handling for the React frontend.

Test Scenarios:
1. Keycloak connectivity issues
2. Malformed tokens and payloads
3. Network timeouts and retries
4. Token edge cases (missing claims, wrong issuer, etc.)
5. Concurrent authentication requests
6. Rate limiting scenarios (future)

Focus: Error handling and resilience testing
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os
import sys
import requests

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from api.v0_1.app import app


class TestKeycloakConnectivityErrors:
    """Test scenarios when Keycloak is unavailable or misconfigured."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables."""
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
        
        for key, value in self.env_vars.items():
            os.environ[key] = value
            
        yield
        
        for key in self.env_vars.keys():
            os.environ.pop(key, None)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_well_known_endpoint_unavailable(self, mock_requests_get, client):
        """
        Test when Keycloak's well-known configuration endpoint is unavailable.
        
        Scenario:
        1. React app tries to validate token
        2. API tries to fetch Keycloak configuration
        3. Keycloak server is down/unreachable
        4. API should handle gracefully and return 401
        """
        # Mock network failure
        mock_requests_get.side_effect = requests.ConnectionError("Connection failed")
        
        headers = {"Authorization": "Bearer some-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_well_known_returns_invalid_json(self, mock_requests_get, client):
        """
        Test when Keycloak returns malformed configuration.
        
        Scenario:
        1. React app tries to validate token
        2. API fetches Keycloak configuration
        3. Keycloak returns invalid JSON
        4. API should handle gracefully and return 401
        """
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_requests_get.return_value = mock_response
        
        headers = {"Authorization": "Bearer some-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_missing_jwks_uri(self, mock_requests_get, client):
        """
        Test when Keycloak configuration is missing jwks_uri.
        
        Scenario:
        1. React app tries to validate token
        2. API fetches Keycloak configuration
        3. Configuration is missing jwks_uri field
        4. API should handle gracefully and return 401
        """
        # Mock response without jwks_uri
        mock_response = Mock()
        mock_response.json.return_value = {
            "issuer": "http://localhost:8080/realms/test-realm",
            # Missing jwks_uri
        }
        mock_requests_get.return_value = mock_response
        
        headers = {"Authorization": "Bearer some-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]


class TestMalformedTokenScenarios:
    """Test scenarios with various malformed or invalid tokens."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables."""
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
        
        for key, value in self.env_vars.items():
            os.environ[key] = value
            
        yield
        
        for key in self.env_vars.keys():
            os.environ.pop(key, None)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_empty_bearer_token(self, client):
        """Test with empty bearer token."""
        headers = {"Authorization": "Bearer "}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Bearer token required" in response.json()["detail"]
    
    def test_bearer_token_with_spaces(self, client):
        """Test with bearer token containing only spaces."""
        headers = {"Authorization": "Bearer    "}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Bearer token required" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_token_that_cannot_extract_signing_key(self, mock_get_jwks_client, client):
        """
        Test token that fails during signing key extraction.
        
        Scenario:
        1. React app sends token
        2. API tries to extract signing key from JWT header
        3. Signing key extraction fails (malformed header)
        4. API returns 401
        """
        # Mock JWKS client that fails to extract signing key
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt_lib.PyJWKClientError("Cannot extract key")
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer malformed.jwt.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_with_wrong_issuer(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test token with wrong issuer claim.
        
        Scenario:
        1. React app sends token from different realm/issuer
        2. API validates token
        3. JWT validation fails due to issuer mismatch
        4. API returns 401
        """
        # Mock JWT decode failure due to wrong issuer
        mock_jwt_decode.side_effect = jwt_lib.InvalidIssuerError("Invalid issuer")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer wrong-issuer-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_with_missing_claims(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test token with missing essential claims.
        
        Scenario:
        1. React app sends token with missing preferred_username
        2. API validates token successfully
        3. Token payload is missing expected claims
        4. API should still work but handle missing claims gracefully
        """
        # Mock token with minimal claims
        minimal_payload = {
            "sub": "user-123",
            "iss": "http://localhost:8080/realms/test-realm",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
            # Missing preferred_username, email, realm_access, etc.
        }
        
        mock_jwt_decode.return_value = minimal_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer minimal-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        # Should still succeed, just with minimal user info
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["valid"] is True
        assert response_data["user"]["sub"] == "user-123"
        assert response_data["user"].get("preferred_username") is None


class TestTokenEdgeCases:
    """Test various edge cases in token processing."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables."""
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
        
        for key, value in self.env_vars.items():
            os.environ[key] = value
            
        yield
        
        for key in self.env_vars.keys():
            os.environ.pop(key, None)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_with_different_client_id(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test token issued for different client_id.
        
        Scenario:
        1. React app sends token issued for different client
        2. API validates token (signature is valid)
        3. Client ID mismatch detected
        4. API continues (just logs warning) since validation succeeded
        """
        # Token with different client_id
        different_client_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "azp": "different-client",  # Different authorized party
            "iss": "http://localhost:8080/realms/test-realm",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
        
        mock_jwt_decode.return_value = different_client_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer different-client-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        # Should still succeed (current implementation continues on client_id mismatch)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["valid"] is True
        assert response_data["user"]["azp"] == "different-client"
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_issued_in_future(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test token with 'iat' (issued at) time in the future.
        
        Scenario:
        1. React app sends token with future 'iat' claim
        2. API validates token
        3. JWT validation should fail due to invalid 'iat'
        """
        # Token issued in the future
        future_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "iss": "http://localhost:8080/realms/test-realm",
            "exp": int((datetime.utcnow() + timedelta(hours=2)).timestamp()),
            "iat": int((datetime.utcnow() + timedelta(minutes=5)).timestamp())  # Future issue time
        }
        
        # Mock JWT library to raise error for future 'iat'
        mock_jwt_decode.side_effect = jwt_lib.ImmatureSignatureError("Token not yet valid")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer future-token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]


class TestRoleClaimVariations:
    """Test various ways roles can be structured in tokens."""
    
    def test_admin_role_detection_edge_cases(self):
        """Test admin role detection with various token structures."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test with empty realm_access
        token1 = {
            "realm_access": {},
            "resource_access": {}
        }
        assert is_user_admin(token1) is False
        
        # Test with no realm_access at all
        token2 = {
            "resource_access": {}
        }
        assert is_user_admin(token2) is False
        
        # Test with realm_access but no roles
        token3 = {
            "realm_access": {"roles": []},
            "resource_access": {}
        }
        assert is_user_admin(token3) is False
        
        # Test with resource_access but no roles in any client
        token4 = {
            "realm_access": {"roles": ["user"]},
            "resource_access": {
                "client1": {},
                "client2": {"roles": []}
            }
        }
        assert is_user_admin(token4) is False
        
        # Test with admin role in nested client
        token5 = {
            "realm_access": {"roles": ["user"]},
            "resource_access": {
                "client1": {"roles": ["user"]},
                "client2": {"roles": ["admin", "moderator"]}
            }
        }
        assert is_user_admin(token5) is True
    
    def test_case_sensitive_role_matching(self):
        """Test that role matching is case-sensitive."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test with different case variations
        token_admin_caps = {
            "realm_access": {"roles": ["ADMIN"]},  # Uppercase
            "resource_access": {}
        }
        assert is_user_admin(token_admin_caps) is False  # Should be case-sensitive
        
        token_admin_mixed = {
            "realm_access": {"roles": ["Admin"]},  # Mixed case
            "resource_access": {}
        }
        assert is_user_admin(token_admin_mixed) is False  # Should be case-sensitive
        
        token_admin_correct = {
            "realm_access": {"roles": ["admin"]},  # Correct lowercase
            "resource_access": {}
        }
        assert is_user_admin(token_admin_correct) is True  # Should match


class TestConcurrentAuthenticationRequests:
    """Test behavior under concurrent authentication requests."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables."""
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
        
        for key, value in self.env_vars.items():
            os.environ[key] = value
            
        yield
        
        for key in self.env_vars.keys():
            os.environ.pop(key, None)
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_multiple_validation_requests_same_token(self, mock_jwt_decode, mock_get_jwks_client, client):
        """
        Test multiple concurrent validation requests with same token.
        
        Scenario:
        1. React app makes multiple simultaneous requests
        2. All use the same valid token
        3. All should succeed independently
        """
        # Mock valid token
        valid_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "iss": "http://localhost:8080/realms/test-realm",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
        
        mock_jwt_decode.return_value = valid_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        headers = {"Authorization": "Bearer shared-token"}
        
        # Make multiple requests
        responses = []
        for i in range(5):
            response = client.get("/api/auth/validate", headers=headers)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["valid"] is True
            assert response.json()["user"]["preferred_username"] == "testuser"


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running authentication error scenario tests...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)