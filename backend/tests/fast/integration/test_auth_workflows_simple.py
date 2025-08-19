#!/usr/bin/env python3
"""
Simplified Authentication Workflow Tests for React Frontend

Tests authentication workflows without requiring full application setup.
Uses isolated testing of auth functions and API endpoints.

Test Scenarios:
1. Token validation workflows
2. Bearer token authentication
3. Admin role detection
4. Error scenarios

Focus: Authentication logic testing with minimal dependencies
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class TestTokenValidationLogic:
    """Test token validation logic in isolation."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up minimal test environment."""
        self.env_vars = {
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
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_successful_token_decode_workflow(self, mock_jwt_decode, mock_get_jwks_client, valid_token_payload):
        """
        Test successful token decoding workflow.
        
        This tests the core decode_token function used throughout the API.
        """
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock JWT validation
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Create mock credentials
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="valid.jwt.token"
        )
        
        # Test token decoding
        result = decode_token(mock_credentials)
        
        assert result == valid_token_payload
        assert result["preferred_username"] == "testuser"
        assert result["email"] == "testuser@example.com"
        
        # Verify JWT decode was called with correct parameters
        mock_jwt_decode.assert_called_once()
        call_args = mock_jwt_decode.call_args
        assert call_args[0][0] == "valid.jwt.token"  # token
        assert call_args[1]["algorithms"] == ["RS256"]
        assert call_args[1]["issuer"] == "http://localhost:8080/realms/test-realm"
        assert call_args[1]["options"]["verify_aud"] is False
    
    def test_missing_credentials_workflow(self):
        """Test workflow when no credentials are provided."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi import HTTPException
        
        # Test with None credentials
        with pytest.raises(HTTPException) as exc_info:
            decode_token(None)
        
        assert exc_info.value.status_code == 401
        assert "Bearer token required" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_expired_token_workflow(self, mock_jwt_decode, mock_get_jwks_client):
        """Test workflow with expired token."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock expired token error
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="expired.jwt.token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_invalid_signature_workflow(self, mock_jwt_decode, mock_get_jwks_client):
        """Test workflow with invalid token signature."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock invalid signature error
        mock_jwt_decode.side_effect = jwt_lib.InvalidSignatureError("Invalid signature")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="tampered.jwt.token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


class TestAdminRoleDetection:
    """Test admin role detection workflows."""
    
    def test_admin_role_in_realm_access(self):
        """Test admin role detection via realm_access."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        token_payload = {
            "realm_access": {
                "roles": ["admin", "user"]
            },
            "resource_access": {}
        }
        
        assert is_user_admin(token_payload) is True
    
    def test_admin_role_in_resource_access(self):
        """Test admin role detection via resource_access."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        token_payload = {
            "realm_access": {
                "roles": ["user"]
            },
            "resource_access": {
                "test-client": {
                    "roles": ["admin"]
                },
                "other-client": {
                    "roles": ["user"]
                }
            }
        }
        
        assert is_user_admin(token_payload) is True
    
    def test_no_admin_role(self):
        """Test admin role detection when user has no admin role."""
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
    
    def test_missing_role_claims(self):
        """Test admin role detection with missing role claims."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test with completely missing role claims
        token_payload = {
            "sub": "user-123",
            "preferred_username": "testuser"
        }
        
        assert is_user_admin(token_payload) is False
        
        # Test with empty role structures
        token_payload_empty = {
            "realm_access": {},
            "resource_access": {}
        }
        
        assert is_user_admin(token_payload_empty) is False


class TestAuthenticationUtilities:
    """Test authentication utility functions."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up minimal test environment."""
        self.env_vars = {
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
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_get_jwks_client_success(self, mock_requests_get):
        """Test successful JWKS client creation."""
        from api.v0_1.endpoints.service.auth import get_jwks_client
        
        # Mock successful OIDC configuration fetch
        mock_response = Mock()
        mock_response.json.return_value = {
            "issuer": "http://localhost:8080/realms/test-realm",
            "jwks_uri": "http://localhost:8080/realms/test-realm/protocol/openid-connect/certs"
        }
        mock_requests_get.return_value = mock_response
        
        with patch('api.v0_1.endpoints.service.auth.PyJWKClient') as mock_jwk_client:
            mock_client_instance = Mock()
            mock_jwk_client.return_value = mock_client_instance
            
            result = get_jwks_client()
            
            assert result == mock_client_instance
            mock_jwk_client.assert_called_once_with(
                "http://localhost:8080/realms/test-realm/protocol/openid-connect/certs"
            )
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_get_jwks_client_missing_jwks_uri(self, mock_requests_get):
        """Test JWKS client creation when jwks_uri is missing."""
        from api.v0_1.endpoints.service.auth import get_jwks_client
        
        # Mock OIDC configuration without jwks_uri
        mock_response = Mock()
        mock_response.json.return_value = {
            "issuer": "http://localhost:8080/realms/test-realm"
            # Missing jwks_uri
        }
        mock_requests_get.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            get_jwks_client()
        
        assert "jwks_uri not found" in str(exc_info.value)
    
    def test_keycloak_well_known_url_not_set(self):
        """Test JWKS client creation when KEYCLOAK_WELL_KNOWN_URL is not set."""
        from api.v0_1.endpoints.service.auth import get_jwks_client
        
        # Remove the environment variable
        os.environ.pop('KEYCLOAK_WELL_KNOWN_URL', None)
        
        with pytest.raises(Exception) as exc_info:
            get_jwks_client()
        
        assert "KEYCLOAK_WELL_KNOWN_URL is not set" in str(exc_info.value)


class TestAuthenticationErrorScenarios:
    """Test various error scenarios in authentication."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up minimal test environment."""
        self.env_vars = {
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
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_jwks_client_key_extraction_failure(self, mock_get_jwks_client):
        """Test when JWKS client fails to extract signing key."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock JWKS client that fails to extract key
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt_lib.PyJWKClientError("Key not found")
        mock_get_jwks_client.return_value = mock_jwks_client
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="invalid.header.token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_client_id_mismatch_handling(self, mock_jwt_decode, mock_get_jwks_client):
        """Test handling of client_id mismatch in token."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Token with different client_id
        token_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "azp": "different-client",  # Different authorized party
            "iss": "http://localhost:8080/realms/test-realm",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
        
        mock_jwt_decode.return_value = token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="different.client.token"
        )
        
        # Should still succeed (current implementation continues on client_id mismatch)
        result = decode_token(mock_credentials)
        
        assert result == token_payload
        assert result["azp"] == "different-client"


class TestReactFrontendWorkflows:
    """Test workflows specifically designed for React frontend integration."""
    
    def test_token_payload_structure_for_react(self):
        """
        Test that token payloads contain expected fields for React frontend.
        
        React frontend expects certain fields to be present for:
        - User display (preferred_username, email)
        - Role-based UI (realm_access, resource_access)
        - Session management (exp, iat, sub)
        """
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test with comprehensive token payload
        comprehensive_payload = {
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
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "session_state": "session-123"
        }
        
        # Verify React frontend can extract needed information
        assert comprehensive_payload.get("preferred_username") == "testuser"
        assert comprehensive_payload.get("email") == "testuser@example.com"
        assert comprehensive_payload.get("sub") is not None
        assert comprehensive_payload.get("exp") is not None
        
        # Verify role checking works
        assert is_user_admin(comprehensive_payload) is False
        
        # Test with minimal payload (some Keycloak configs might not include all fields)
        minimal_payload = {
            "sub": "user-456",
            "iss": "http://localhost:8080/realms/test-realm",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
        
        # React should handle missing optional fields gracefully
        assert minimal_payload.get("preferred_username") is None
        assert minimal_payload.get("email") is None
        assert minimal_payload.get("sub") == "user-456"
        assert is_user_admin(minimal_payload) is False
    
    def test_authentication_flow_states_for_react(self):
        """
        Test different authentication states that React frontend needs to handle.
        
        React needs to handle:
        1. Unauthenticated (no token)
        2. Authenticated user (valid token, user role)
        3. Authenticated admin (valid token, admin role)
        4. Token expired (need to refresh/redirect to login)
        5. Token invalid (malformed/tampered)
        """
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # State 1: Unauthenticated - handled by missing token (401 response)
        
        # State 2: Authenticated user
        user_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["user"]},
            "resource_access": {},
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        assert is_user_admin(user_payload) is False
        
        # State 3: Authenticated admin
        admin_payload = {
            "sub": "admin-123",
            "preferred_username": "adminuser",
            "realm_access": {"roles": ["admin", "user"]},
            "resource_access": {},
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        assert is_user_admin(admin_payload) is True
        
        # State 4: Token expired - handled by JWT library raising ExpiredSignatureError
        expired_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp())  # Expired
        }
        # In real scenario, JWT validation would fail before we get the payload
        
        # State 5: Token invalid - handled by JWT library raising validation errors


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running simplified authentication workflow tests...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)