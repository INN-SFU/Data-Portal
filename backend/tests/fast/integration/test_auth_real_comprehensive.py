#!/usr/bin/env python3
"""
Comprehensive Authentication Tests with Direct Token Validation

Uses the isolated authentication function testing approach from test_auth_workflows_simple.py
but provides comprehensive coverage of React frontend authentication workflows.

This approach tests the core authentication logic without requiring full application setup
or external Keycloak connectivity, making it fast and reliable.
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


@pytest.fixture(autouse=True)
def setup_keycloak_environment():
    """Set up Keycloak environment variables for all tests."""
    env_vars = {
        'KEYCLOAK_DOMAIN': 'http://localhost:8080',
        'KEYCLOAK_REALM': 'ams-portal',
        'KEYCLOAK_UI_CLIENT_ID': 'ams-portal-ui',
        'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/ams-portal/.well-known/openid-configuration'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        
    yield
    
    for key in env_vars.keys():
        os.environ.pop(key, None)


@pytest.fixture
def test_signing_key():
    """Consistent test signing key for JWT mocking."""
    return "test-rsa-signing-key-for-comprehensive-tests"


@pytest.fixture
def mock_jwks_setup(test_signing_key):
    """Setup mock JWKS client consistently."""
    def _setup_mocks(mock_get_jwks_client, mock_jwt_decode, token_payload):
        # Setup JWT decode
        mock_jwt_decode.return_value = token_payload
        
        # Setup JWKS client
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = test_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        return mock_jwks_client
    return _setup_mocks


@pytest.fixture
def admin_user_payload():
    """Admin user token payload for comprehensive testing."""
    return {
        "sub": "admin-uuid-123",
        "preferred_username": "admin",
        "email": "admin@localhost",
        "given_name": "Admin",
        "family_name": "User",
        "realm_access": {
            "roles": ["admin", "user"]
        },
        "resource_access": {
            "ams-portal-ui": {
                "roles": ["admin", "user"]
            }
        },
        "iss": "http://localhost:8080/realms/ams-portal",
        "aud": "ams-portal-ui",
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "session_state": "test-session-123"
    }


@pytest.fixture
def regular_user_payload():
    """Regular user token payload for comprehensive testing."""
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
            "ams-portal-ui": {
                "roles": ["user"]
            }
        },
        "iss": "http://localhost:8080/realms/ams-portal",
        "aud": "ams-portal-ui", 
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "session_state": "test-session-456"
    }


class TestAuthenticationFunctionWorkflows:
    """Test authentication functions directly for comprehensive coverage."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_admin_token_validation_workflow(self, mock_jwt_decode, mock_get_jwks_client, 
                                           mock_jwks_setup, admin_user_payload):
        """Test complete admin token validation workflow."""
        from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Setup mocks
        mock_jwks_setup(mock_get_jwks_client, mock_jwt_decode, admin_user_payload)
        
        # Create mock credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="admin.jwt.token"
        )
        
        # Test token decoding
        decoded_token = decode_token(credentials)
        
        # Verify token structure for React frontend
        assert decoded_token["preferred_username"] == "admin"
        assert decoded_token["email"] == "admin@localhost"
        assert "admin" in decoded_token["realm_access"]["roles"]
        assert "user" in decoded_token["realm_access"]["roles"]
        
        # Test admin role detection
        assert is_user_admin(decoded_token) is True
        
        # Verify JWT validation was called correctly
        mock_jwt_decode.assert_called_once()
        call_args = mock_jwt_decode.call_args
        assert call_args[0][0] == "admin.jwt.token"
        assert call_args[1]["algorithms"] == ["RS256"]
        assert call_args[1]["issuer"] == "http://localhost:8080/realms/ams-portal"
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_regular_user_token_validation_workflow(self, mock_jwt_decode, mock_get_jwks_client,
                                                  mock_jwks_setup, regular_user_payload):
        """Test complete regular user token validation workflow."""
        from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Setup mocks
        mock_jwks_setup(mock_get_jwks_client, mock_jwt_decode, regular_user_payload)
        
        # Create mock credentials  
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="user.jwt.token"
        )
        
        # Test token decoding
        decoded_token = decode_token(credentials)
        
        # Verify token structure for React frontend
        assert decoded_token["preferred_username"] == "testuser"
        assert decoded_token["email"] == "testuser@example.com"
        assert decoded_token["given_name"] == "Test"
        assert decoded_token["family_name"] == "User"
        assert "user" in decoded_token["realm_access"]["roles"]
        assert "admin" not in decoded_token["realm_access"]["roles"]
        
        # Test admin role detection
        assert is_user_admin(decoded_token) is False
        
        # React UI data extraction
        display_name = f"{decoded_token['given_name']} {decoded_token['family_name']}"
        assert display_name == "Test User"
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_expired_token_error_workflow(self, mock_jwt_decode, mock_get_jwks_client):
        """Test expired token error handling workflow."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock expired token error
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token has expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="expired.jwt.token"
        )
        
        # Test that expired token raises 401
        with pytest.raises(HTTPException) as exc_info:
            decode_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
        
        # React should handle this by clearing token and redirecting to login
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_invalid_signature_error_workflow(self, mock_jwt_decode, mock_get_jwks_client):
        """Test invalid signature error handling workflow."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock invalid signature error
        mock_jwt_decode.side_effect = jwt_lib.InvalidSignatureError("Invalid signature")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="tampered.jwt.token"
        )
        
        # Test that invalid signature raises 401
        with pytest.raises(HTTPException) as exc_info:
            decode_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


class TestRoleBasedAccessPatterns:
    """Test role-based access patterns for React frontend."""
    
    def test_admin_role_detection_comprehensive(self):
        """Test comprehensive admin role detection scenarios."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test admin role in realm_access
        token_realm_admin = {
            "realm_access": {"roles": ["admin", "user"]},
            "resource_access": {}
        }
        assert is_user_admin(token_realm_admin) is True
        
        # Test admin role in resource_access  
        token_resource_admin = {
            "realm_access": {"roles": ["user"]},
            "resource_access": {
                "ams-portal-ui": {"roles": ["admin", "user"]},
                "other-client": {"roles": ["user"]}
            }
        }
        assert is_user_admin(token_resource_admin) is True
        
        # Test no admin role
        token_no_admin = {
            "realm_access": {"roles": ["user"]},
            "resource_access": {
                "ams-portal-ui": {"roles": ["user"]}
            }
        }
        assert is_user_admin(token_no_admin) is False
        
        # Test missing role claims
        token_missing_roles = {
            "sub": "user-123",
            "preferred_username": "testuser"
        }
        assert is_user_admin(token_missing_roles) is False
    
    def test_react_ui_role_based_rendering_logic(self, admin_user_payload, regular_user_payload):
        """Test React UI role-based rendering logic."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Admin user UI logic
        admin_roles = admin_user_payload.get("realm_access", {}).get("roles", [])
        is_admin = is_user_admin(admin_user_payload)
        
        # React admin UI decisions
        should_show_admin_panel = is_admin
        should_show_user_management = is_admin
        should_show_policy_management = is_admin
        can_create_endpoints = is_admin
        
        assert should_show_admin_panel is True
        assert should_show_user_management is True
        assert should_show_policy_management is True
        assert can_create_endpoints is True
        
        # Regular user UI logic
        user_roles = regular_user_payload.get("realm_access", {}).get("roles", [])
        is_regular_user = not is_user_admin(regular_user_payload)
        
        # React user UI decisions
        should_show_admin_panel = not is_regular_user
        should_show_user_dashboard = is_regular_user
        can_view_own_data = is_regular_user
        
        assert should_show_admin_panel is False
        assert should_show_user_dashboard is True
        assert can_view_own_data is True


class TestReactFrontendIntegrationPatterns:
    """Test specific React frontend integration patterns."""
    
    def test_user_profile_data_extraction_patterns(self, admin_user_payload, regular_user_payload):
        """Test user profile data extraction for React components."""
        
        # Admin user data extraction
        admin_user_id = admin_user_payload["sub"]
        admin_email = admin_user_payload["email"]
        admin_username = admin_user_payload["preferred_username"]
        admin_first_name = admin_user_payload.get("given_name", "")
        admin_last_name = admin_user_payload.get("family_name", "")
        admin_full_name = f"{admin_first_name} {admin_last_name}".strip()
        admin_display_name = admin_full_name if admin_full_name else admin_username
        
        assert admin_user_id == "admin-uuid-123"
        assert admin_email == "admin@localhost"
        assert admin_username == "admin"
        assert admin_display_name == "Admin User"
        
        # Regular user data extraction
        user_user_id = regular_user_payload["sub"]
        user_email = regular_user_payload["email"]
        user_username = regular_user_payload["preferred_username"]
        user_first_name = regular_user_payload.get("given_name", "")
        user_last_name = regular_user_payload.get("family_name", "")
        user_full_name = f"{user_first_name} {user_last_name}".strip()
        user_display_name = user_full_name if user_full_name else user_username
        
        assert user_user_id == "user-uuid-456"
        assert user_email == "testuser@example.com"
        assert user_username == "testuser"
        assert user_display_name == "Test User"
    
    def test_token_expiry_management_for_react(self, admin_user_payload):
        """Test token expiry management patterns for React."""
        
        # Extract token timing information
        exp_timestamp = admin_user_payload["exp"]
        iat_timestamp = admin_user_payload["iat"]
        
        # React token refresh logic simulation
        now = datetime.utcnow().timestamp()
        token_age = now - iat_timestamp
        time_until_expiry = exp_timestamp - now
        refresh_threshold = 10 * 60  # 10 minutes
        
        # Token validity checks
        is_expired = exp_timestamp < now
        is_valid = not is_expired
        should_refresh_soon = time_until_expiry < refresh_threshold
        
        assert is_expired is False
        assert is_valid is True
        assert token_age >= 0
        assert time_until_expiry > 0
    
    def test_authentication_state_management_for_react(self):
        """Test authentication state management patterns for React."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # React authentication states
        
        # State 1: Unauthenticated (no token)
        auth_state_unauthenticated = {
            "isAuthenticated": False,
            "user": None,
            "isAdmin": False,
            "shouldRedirectToLogin": True
        }
        
        # State 2: Authenticated regular user
        user_token = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["user"]},
            "resource_access": {}
        }
        auth_state_user = {
            "isAuthenticated": True,
            "user": user_token,
            "isAdmin": is_user_admin(user_token),
            "shouldRedirectToLogin": False
        }
        
        # State 3: Authenticated admin user
        admin_token = {
            "sub": "admin-123",
            "preferred_username": "admin",
            "realm_access": {"roles": ["admin", "user"]},
            "resource_access": {}
        }
        auth_state_admin = {
            "isAuthenticated": True,
            "user": admin_token,
            "isAdmin": is_user_admin(admin_token),
            "shouldRedirectToLogin": False
        }
        
        # Verify state logic
        assert auth_state_unauthenticated["shouldRedirectToLogin"] is True
        assert auth_state_user["isAuthenticated"] is True
        assert auth_state_user["isAdmin"] is False
        assert auth_state_admin["isAuthenticated"] is True
        assert auth_state_admin["isAdmin"] is True


class TestErrorHandlingScenarios:
    """Test comprehensive error handling scenarios."""
    
    def test_missing_credentials_handling(self):
        """Test handling of missing credentials."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi import HTTPException
        
        # Test with None credentials
        with pytest.raises(HTTPException) as exc_info:
            decode_token(None)
        
        assert exc_info.value.status_code == 401
        assert "Bearer token required" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_jwks_client_errors(self, mock_get_jwks_client):
        """Test JWKS client error scenarios."""
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Mock JWKS client failure
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt_lib.PyJWKClientError("Key not found")
        mock_get_jwks_client.return_value = mock_jwks_client
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.key.token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_connectivity_errors(self, mock_requests_get):
        """Test Keycloak connectivity error scenarios."""
        from api.v0_1.endpoints.service.auth import get_jwks_client
        
        # Mock network failure
        mock_requests_get.side_effect = Exception("Connection refused")
        
        with pytest.raises(Exception) as exc_info:
            get_jwks_client()
        
        assert "Connection refused" in str(exc_info.value)


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